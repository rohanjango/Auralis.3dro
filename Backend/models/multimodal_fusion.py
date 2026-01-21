# ==============================
# 📄 models/multimodal_fusion.py
# ==============================
# UPGRADE 5: Multi-Modal Fusion with Cross-Attention
# ==============================

import tensorflow as tf
from tensorflow.keras import layers, Model
import numpy as np
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))
from config import config
from .audio_transformer import AudioTransformerEncoder

class CrossModalAttention(layers.Layer):
    """
    Cross-modal attention for fusing different modalities.
    Allows each modality to attend to others.
    """
    
    def __init__(
        self,
        d_model: int = 256,
        num_heads: int = 8,
        dropout: float = 0.1,
        **kwargs
    ):
        super().__init__(**kwargs)
        
        self.d_model = d_model
        self.num_heads = num_heads
        self.dropout_rate = dropout
        
        # Cross-attention: query from modality A, key/value from modality B
        self.cross_attn_ab = layers.MultiHeadAttention(
            num_heads=num_heads,
            key_dim=d_model // num_heads,
            dropout=dropout,
            name='cross_attn_a_to_b'
        )
        
        self.cross_attn_ba = layers.MultiHeadAttention(
            num_heads=num_heads,
            key_dim=d_model // num_heads,
            dropout=dropout,
            name='cross_attn_b_to_a'
        )
        
        # Layer norms
        self.norm_a = layers.LayerNormalization(epsilon=1e-6)
        self.norm_b = layers.LayerNormalization(epsilon=1e-6)
        
        # Feed-forward for each modality
        self.ffn_a = tf.keras.Sequential([
            layers.Dense(d_model * 4, activation='gelu'),
            layers.Dropout(dropout),
            layers.Dense(d_model),
            layers.Dropout(dropout)
        ])
        
        self.ffn_b = tf.keras.Sequential([
            layers.Dense(d_model * 4, activation='gelu'),
            layers.Dropout(dropout),
            layers.Dense(d_model),
            layers.Dropout(dropout)
        ])
        
        self.norm_a2 = layers.LayerNormalization(epsilon=1e-6)
        self.norm_b2 = layers.LayerNormalization(epsilon=1e-6)
        
    def call(self, features_a, features_b, training=False):
        """
        Cross-modal attention between two modalities.
        
        Args:
            features_a: [batch, seq_len_a, d_model] or [batch, d_model]
            features_b: [batch, seq_len_b, d_model] or [batch, d_model]
            training: Whether in training mode
            
        Returns:
            Updated features for both modalities
        """
        # Ensure 3D tensors
        if len(features_a.shape) == 2:
            features_a = tf.expand_dims(features_a, axis=1)
        if len(features_b.shape) == 2:
            features_b = tf.expand_dims(features_b, axis=1)
        
        # A attends to B
        a_norm = self.norm_a(features_a)
        b_for_a = self.cross_attn_ab(
            query=a_norm,
            key=features_b,
            value=features_b,
            training=training
        )
        features_a = features_a + b_for_a
        
        # B attends to A
        b_norm = self.norm_b(features_b)
        a_for_b = self.cross_attn_ba(
            query=b_norm,
            key=features_a,
            value=features_a,
            training=training
        )
        features_b = features_b + a_for_b
        
        # Feed-forward
        features_a = features_a + self.ffn_a(self.norm_a2(features_a), training=training)
        features_b = features_b + self.ffn_b(self.norm_b2(features_b), training=training)
        
        return features_a, features_b
    
    def get_config(self):
        config = super().get_config()
        config.update({
            'd_model': self.d_model,
            'num_heads': self.num_heads,
            'dropout': self.dropout_rate
        })
        return config


class GatedFusion(layers.Layer):
    """
    Gated fusion mechanism for combining multiple modalities.
    Learns to weight different modalities based on their relevance.
    """
    
    def __init__(self, d_model: int = 256, num_modalities: int = 3, **kwargs):
        super().__init__(**kwargs)
        
        self.d_model = d_model
        self.num_modalities = num_modalities
        
        # Gate network
        self.gate_fc = layers.Dense(num_modalities, activation='softmax')
        
        # Output projection
        self.output_fc = layers.Dense(d_model)
        self.output_norm = layers.LayerNormalization()
        
    def call(self, modality_features, training=False):
        """
        Fuse multiple modalities with learned gates.
        
        Args:
            modality_features: List of [batch, d_model] tensors
            
        Returns:
            Fused features [batch, d_model]
        """
        # Stack modalities
        stacked = tf.stack(modality_features, axis=1)  # [batch, num_modalities, d_model]
        
        # Compute gate weights from concatenated features
        concat = tf.concat(modality_features, axis=-1)
        gate_weights = self.gate_fc(concat)  # [batch, num_modalities]
        gate_weights = tf.expand_dims(gate_weights, axis=-1)  # [batch, num_modalities, 1]
        
        # Weighted sum
        fused = tf.reduce_sum(stacked * gate_weights, axis=1)  # [batch, d_model]
        
        # Output projection
        fused = self.output_fc(fused)
        fused = self.output_norm(fused)
        
        return fused


class MultiModalFusionNetwork(Model):
    """
    Advanced multi-modal fusion network.
    Combines audio, text, and sound classification features.
    """
    
    def __init__(
        self,
        d_model: int = None,
        num_cross_attention_layers: int = None,
        num_locations: int = None,
        num_situations: int = None,
        use_transformer_encoder: bool = True,
        name: str = "multimodal_fusion_network"
    ):
        super().__init__(name=name)
        
        # Config
        self.d_model = d_model or config.model.d_model
        self.num_cross_layers = num_cross_attention_layers or config.model.num_cross_attention_layers
        self.num_locations = num_locations or config.labels.num_locations
        self.num_situations = num_situations or config.labels.num_situations
        self.use_transformer = use_transformer_encoder
        
        # Audio encoder
        if use_transformer_encoder:
            self.audio_encoder = AudioTransformerEncoder(
                d_model=self.d_model,
                num_layers=4
            )
        else:
            self.audio_encoder = tf.keras.Sequential([
                layers.Conv1D(64, 3, padding='same', activation='relu'),
                layers.MaxPooling1D(2),
                layers.Conv1D(128, 3, padding='same', activation='relu'),
                layers.MaxPooling1D(2),
                layers.Conv1D(256, 3, padding='same', activation='relu'),
                layers.GlobalAveragePooling1D(),
                layers.Dense(self.d_model),
                layers.LayerNormalization()
            ])
        
        # Text encoder
        self.text_encoder = tf.keras.Sequential([
            layers.Dense(512, activation='gelu'),
            layers.LayerNormalization(),
            layers.Dropout(0.1),
            layers.Dense(self.d_model, activation='gelu'),
            layers.LayerNormalization()
        ])
        
        # Sound encoder
        self.sound_encoder = tf.keras.Sequential([
            layers.Dense(256, activation='gelu'),
            layers.LayerNormalization(),
            layers.Dropout(0.1),
            layers.Dense(self.d_model, activation='gelu'),
            layers.LayerNormalization()
        ])
        
        # Cross-modal attention layers
        self.cross_attention_layers = [
            CrossModalAttention(self.d_model, num_heads=8, dropout=0.1)
            for _ in range(self.num_cross_layers)
        ]
        
        # Gated fusion
        self.gated_fusion = GatedFusion(self.d_model, num_modalities=3)
        
        # Classification heads
        self.classifier = tf.keras.Sequential([
            layers.Dense(512, activation='gelu'),
            layers.BatchNormalization(),
            layers.Dropout(0.3),
            layers.Dense(256, activation='gelu'),
            layers.BatchNormalization(),
            layers.Dropout(0.2),
        ])
        
        self.location_head = layers.Dense(self.num_locations, activation='softmax', name='location')
        self.situation_head = layers.Dense(self.num_situations, activation='softmax', name='situation')
        self.confidence_head = layers.Dense(1, activation='sigmoid', name='confidence')
        self.emergency_head = layers.Dense(1, activation='sigmoid', name='emergency')
        
    def call(self, inputs, training=False):
        """
        Forward pass.
        
        Args:
            inputs: Dictionary or tuple with:
                - mel_spectrogram: [batch, time, freq]
                - text_embedding: [batch, embed_dim]
                - sound_scores: [batch, num_classes]
                
        Returns:
            Dictionary with predictions
        """
        # Unpack inputs
        if isinstance(inputs, dict):
            mel_spec = inputs.get('mel_spectrogram')
            text_embed = inputs.get('text_embedding')
            sound_scores = inputs.get('sound_scores')
        else:
            mel_spec, text_embed, sound_scores = inputs
        
        # Encode each modality
        audio_feat = self.audio_encoder(mel_spec, training=training)
        text_feat = self.text_encoder(text_embed, training=training)
        sound_feat = self.sound_encoder(sound_scores, training=training)
        
        # Cross-modal attention between audio and text
        for layer in self.cross_attention_layers:
            audio_feat, text_feat = layer(audio_feat, text_feat, training=training)
        
        # Squeeze if needed
        if len(audio_feat.shape) == 3:
            audio_feat = tf.squeeze(audio_feat, axis=1)
        if len(text_feat.shape) == 3:
            text_feat = tf.squeeze(text_feat, axis=1)
        
        # Gated fusion
        fused = self.gated_fusion([audio_feat, text_feat, sound_feat], training=training)
        
        # Classification
        features = self.classifier(fused, training=training)
        
        return {
            'location': self.location_head(features),
            'situation': self.situation_head(features),
            'confidence': tf.squeeze(self.confidence_head(features), axis=-1),
            'emergency': tf.squeeze(self.emergency_head(features), axis=-1)
        }
    
    def get_config(self):
        return {
            'd_model': self.d_model,
            'num_cross_attention_layers': self.num_cross_layers,
            'num_locations': self.num_locations,
            'num_situations': self.num_situations,
            'use_transformer_encoder': self.use_transformer
        }


# ==============================
# 🧪 TESTING
# ==============================
if __name__ == "__main__":
    print("=" * 60)
    print("Testing Multi-Modal Fusion Network")
    print("=" * 60)
    
    # Test input
    batch_size = 4
    time_steps = 100
    mel_bins = 80
    text_dim = 768
    sound_classes = 521
    
    inputs = {
        'mel_spectrogram': tf.random.normal([batch_size, time_steps, mel_bins]),
        'text_embedding': tf.random.normal([batch_size, text_dim]),
        'sound_scores': tf.random.normal([batch_size, sound_classes])
    }
    
    # Test model
    model = MultiModalFusionNetwork(use_transformer_encoder=False)
    output = model(inputs, training=False)
    
    print(f"\nInput shapes:")
    for k, v in inputs.items():
        print(f"  {k}: {v.shape}")
    
    print(f"\nOutput shapes:")
    for k, v in output.items():
        print(f"  {k}: {v.shape}")
    
    print(f"\nModel parameters: {model.count_params():,}")
    
    # Test with transformer encoder
    print("\n" + "-" * 40)
    print("Testing with Transformer Encoder:")
    model_transformer = MultiModalFusionNetwork(use_transformer_encoder=True)
    output = model_transformer(inputs, training=False)
    print(f"Parameters: {model_transformer.count_params():,}")
    
    print("=" * 60)