# ==============================
# 📄 models/audio_transformer.py
# ==============================
# UPGRADE 3: Transformer-Based Audio Encoder
# ==============================

import tensorflow as tf
from tensorflow.keras import layers
import numpy as np
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))
from config import config

class TransformerEncoderLayer(layers.Layer):
    """Single transformer encoder layer with pre-norm architecture"""
    
    def __init__(
        self,
        d_model: int,
        num_heads: int,
        dff: int,
        dropout_rate: float = 0.1,
        **kwargs
    ):
        super().__init__(**kwargs)
        
        self.d_model = d_model
        self.num_heads = num_heads
        self.dff = dff
        self.dropout_rate = dropout_rate
        
        # Multi-head self-attention
        self.mha = layers.MultiHeadAttention(
            num_heads=num_heads,
            key_dim=d_model // num_heads,
            dropout=dropout_rate
        )
        
        # Feed-forward network
        self.ffn = tf.keras.Sequential([
            layers.Dense(dff, activation='gelu'),
            layers.Dropout(dropout_rate),
            layers.Dense(d_model),
            layers.Dropout(dropout_rate)
        ])
        
        # Layer normalization (pre-norm)
        self.norm1 = layers.LayerNormalization(epsilon=1e-6)
        self.norm2 = layers.LayerNormalization(epsilon=1e-6)
        
        # Dropout for residual connections
        self.dropout1 = layers.Dropout(dropout_rate)
        self.dropout2 = layers.Dropout(dropout_rate)
        
    def call(self, x, training=False, return_attention=False):
        """
        Forward pass.
        
        Args:
            x: Input tensor [batch, seq_len, d_model]
            training: Whether in training mode
            return_attention: Whether to return attention weights
            
        Returns:
            Output tensor and optionally attention weights
        """
        # Pre-norm multi-head attention
        x_norm = self.norm1(x)
        attn_output, attn_weights = self.mha(
            x_norm, x_norm, x_norm,
            return_attention_scores=True,
            training=training
        )
        attn_output = self.dropout1(attn_output, training=training)
        x = x + attn_output  # Residual connection
        
        # Pre-norm feed-forward
        x_norm = self.norm2(x)
        ffn_output = self.ffn(x_norm, training=training)
        x = x + ffn_output  # Residual connection
        
        if return_attention:
            return x, attn_weights
        return x
    
    def get_config(self):
        config = super().get_config()
        config.update({
            'd_model': self.d_model,
            'num_heads': self.num_heads,
            'dff': self.dff,
            'dropout_rate': self.dropout_rate
        })
        return config


class AudioTransformerEncoder(tf.keras.Model):
    """
    Transformer encoder for audio sequences.
    Converts mel spectrograms into fixed-size embeddings.
    """
    
    def __init__(
        self,
        num_layers: int = None,
        d_model: int = None,
        num_heads: int = None,
        dff: int = None,
        max_seq_len: int = 1000,
        dropout_rate: float = None,
        name: str = "audio_transformer_encoder"
    ):
        super().__init__(name=name)
        
        # Get config values
        self.num_layers = num_layers or config.model.transformer_layers
        self.d_model = d_model or config.model.d_model
        self.num_heads = num_heads or config.model.num_heads
        self.dff = dff or config.model.dff
        self.dropout_rate = dropout_rate or config.model.dropout_rate
        self.max_seq_len = max_seq_len
        
        # Input projection (from mel bins to d_model)
        self.input_projection = layers.Dense(self.d_model, name='input_projection')
        
        # Convolutional subsampling (reduce sequence length)
        self.conv_subsample = tf.keras.Sequential([
            layers.Conv1D(self.d_model, 3, strides=2, padding='same', activation='gelu'),
            layers.Conv1D(self.d_model, 3, strides=2, padding='same', activation='gelu'),
        ], name='conv_subsample')
        
        # Positional encoding
        self.pos_encoding = self._create_positional_encoding(max_seq_len, self.d_model)
        self.pos_dropout = layers.Dropout(self.dropout_rate)
        
        # Transformer encoder layers
        self.encoder_layers = [
            TransformerEncoderLayer(
                self.d_model,
                self.num_heads,
                self.dff,
                self.dropout_rate,
                name=f'transformer_layer_{i}'
            )
            for i in range(self.num_layers)
        ]
        
        # Output normalization
        self.output_norm = layers.LayerNormalization(epsilon=1e-6)
        
        # Pooling strategies
        self.cls_token = self.add_weight(
            name='cls_token',
            shape=(1, 1, self.d_model),
            initializer='zeros',
            trainable=True
        )
        
    def _create_positional_encoding(self, max_len: int, d_model: int):
        """Create sinusoidal positional encoding"""
        position = np.arange(max_len)[:, np.newaxis]
        div_term = np.exp(np.arange(0, d_model, 2) * -(np.log(10000.0) / d_model))
        
        pos_encoding = np.zeros((max_len, d_model))
        pos_encoding[:, 0::2] = np.sin(position * div_term)
        pos_encoding[:, 1::2] = np.cos(position * div_term)
        
        return tf.constant(pos_encoding[np.newaxis, :, :], dtype=tf.float32)
    
    def call(self, x, training=False, return_attention=False):
        """
        Forward pass.
        
        Args:
            x: Mel spectrogram [batch, time, freq]
            training: Whether in training mode
            return_attention: Whether to return attention weights
            
        Returns:
            Audio embedding [batch, d_model] and optionally attention weights
        """
        batch_size = tf.shape(x)[0]
        
        # Project to model dimension
        x = self.input_projection(x)
        
        # Convolutional subsampling
        x = self.conv_subsample(x)
        seq_len = tf.shape(x)[1]
        
        # Add CLS token
        cls_tokens = tf.tile(self.cls_token, [batch_size, 1, 1])
        x = tf.concat([cls_tokens, x], axis=1)
        
        # Add positional encoding
        x = x + self.pos_encoding[:, :seq_len + 1, :]
        x = self.pos_dropout(x, training=training)
        
        # Apply transformer layers
        attention_weights = []
        for layer in self.encoder_layers:
            if return_attention:
                x, attn = layer(x, training=training, return_attention=True)
                attention_weights.append(attn)
            else:
                x = layer(x, training=training)
        
        # Output normalization
        x = self.output_norm(x)
        
        # Extract CLS token embedding
        cls_output = x[:, 0, :]
        
        if return_attention:
            return cls_output, attention_weights
        return cls_output
    
    def get_attention_maps(self, x):
        """Get attention maps for visualization"""
        _, attention_weights = self(x, training=False, return_attention=True)
        return attention_weights
    
    def get_config(self):
        return {
            'num_layers': self.num_layers,
            'd_model': self.d_model,
            'num_heads': self.num_heads,
            'dff': self.dff,
            'max_seq_len': self.max_seq_len,
            'dropout_rate': self.dropout_rate
        }
    
    @classmethod
    def from_config(cls, config):
        return cls(**config)


# ==============================
# 🎯 SPECIALIZED AUDIO ENCODERS
# ==============================
class ConvolutionalAudioEncoder(tf.keras.Model):
    """Lightweight CNN-based audio encoder for fast inference"""
    
    def __init__(self, d_model: int = 256, name: str = "conv_audio_encoder"):
        super().__init__(name=name)
        
        self.d_model = d_model
        
        self.conv_blocks = tf.keras.Sequential([
            # Block 1
            layers.Conv1D(64, 3, padding='same'),
            layers.BatchNormalization(),
            layers.ReLU(),
            layers.MaxPooling1D(2),
            
            # Block 2
            layers.Conv1D(128, 3, padding='same'),
            layers.BatchNormalization(),
            layers.ReLU(),
            layers.MaxPooling1D(2),
            
            # Block 3
            layers.Conv1D(256, 3, padding='same'),
            layers.BatchNormalization(),
            layers.ReLU(),
            layers.MaxPooling1D(2),
            
            # Block 4
            layers.Conv1D(512, 3, padding='same'),
            layers.BatchNormalization(),
            layers.ReLU(),
            layers.GlobalAveragePooling1D(),
            
            # Output projection
            layers.Dense(d_model),
            layers.LayerNormalization()
        ])
        
    def call(self, x, training=False):
        return self.conv_blocks(x, training=training)


class HybridAudioEncoder(tf.keras.Model):
    """Hybrid CNN + Transformer encoder for balanced performance"""
    
    def __init__(
        self,
        d_model: int = 256,
        num_transformer_layers: int = 2,
        name: str = "hybrid_audio_encoder"
    ):
        super().__init__(name=name)
        
        self.d_model = d_model
        
        # CNN feature extractor
        self.cnn = tf.keras.Sequential([
            layers.Conv1D(64, 3, padding='same', activation='relu'),
            layers.MaxPooling1D(2),
            layers.Conv1D(128, 3, padding='same', activation='relu'),
            layers.MaxPooling1D(2),
            layers.Conv1D(d_model, 3, padding='same', activation='relu'),
        ])
        
        # Transformer layers
        self.transformer_layers = [
            TransformerEncoderLayer(d_model, 4, d_model * 4, 0.1)
            for _ in range(num_transformer_layers)
        ]
        
        # Output
        self.output_norm = layers.LayerNormalization()
        self.pool = layers.GlobalAveragePooling1D()
        
    def call(self, x, training=False):
        # CNN features
        x = self.cnn(x, training=training)
        
        # Transformer refinement
        for layer in self.transformer_layers:
            x = layer(x, training=training)
        
        # Pool to single vector
        x = self.output_norm(x)
        x = self.pool(x)
        
        return x


# ==============================
# 🧪 TESTING
# ==============================
if __name__ == "__main__":
    print("=" * 60)
    print("Testing Audio Transformer Encoder")
    print("=" * 60)
    
    # Test input
    batch_size = 4
    time_steps = 200
    mel_bins = 80
    
    x = tf.random.normal([batch_size, time_steps, mel_bins])
    
    # Test transformer encoder
    print("\n1. AudioTransformerEncoder:")
    encoder = AudioTransformerEncoder()
    output = encoder(x, training=False)
    print(f"   Input shape: {x.shape}")
    print(f"   Output shape: {output.shape}")
    print(f"   Parameters: {encoder.count_params():,}")
    
    # Test with attention
    output, attn = encoder(x, training=False, return_attention=True)
    print(f"   Attention layers: {len(attn)}")
    print(f"   Attention shape: {attn[0].shape}")
    
    # Test CNN encoder
    print("\n2. ConvolutionalAudioEncoder:")
    cnn_encoder = ConvolutionalAudioEncoder()
    output = cnn_encoder(x, training=False)
    print(f"   Output shape: {output.shape}")
    print(f"   Parameters: {cnn_encoder.count_params():,}")
    
    # Test hybrid encoder
    print("\n3. HybridAudioEncoder:")
    hybrid_encoder = HybridAudioEncoder()
    output = hybrid_encoder(x, training=False)
    print(f"   Output shape: {output.shape}")
    print(f"   Parameters: {hybrid_encoder.count_params():,}")
    
    print("=" * 60)