# ==============================
# 📄 models/scene_classifier.py
# ==============================
# UPGRADE 1: Custom Scene Classification Model
# ==============================

import tensorflow as tf
from tensorflow.keras import layers, Model
from tensorflow.keras.optimizers import AdamW
import numpy as np
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))
from config import config

class AuralisSceneClassifier(Model):
    """
    Custom scene classification model that combines:
    - Audio embeddings (from mel spectrogram)
    - Text embeddings (from speech transcription)
    - Sound classification scores (from YAMNet)
    
    Uses multi-task learning for location and situation prediction.
    """
    
    def __init__(
        self,
        num_locations: int = None,
        num_situations: int = None,
        d_model: int = None,
        dropout_rate: float = None,
        name: str = "auralis_scene_classifier"
    ):
        super().__init__(name=name)
        
        # Get config values
        num_locations = num_locations or config.labels.num_locations
        num_situations = num_situations or config.labels.num_situations
        d_model = d_model or config.model.d_model
        dropout_rate = dropout_rate or config.model.dropout_rate
        
        self.num_locations = num_locations
        self.num_situations = num_situations
        self.d_model = d_model
        
        # Audio feature processor (from mel spectrogram)
        self.audio_encoder = tf.keras.Sequential([
            layers.Conv1D(64, 3, padding='same', activation='relu'),
            layers.BatchNormalization(),
            layers.MaxPooling1D(2),
            layers.Conv1D(128, 3, padding='same', activation='relu'),
            layers.BatchNormalization(),
            layers.MaxPooling1D(2),
            layers.Conv1D(256, 3, padding='same', activation='relu'),
            layers.BatchNormalization(),
            layers.GlobalAveragePooling1D(),
            layers.Dense(d_model, activation='gelu'),
            layers.BatchNormalization(),
            layers.Dropout(dropout_rate),
        ], name='audio_encoder')
        
        # Text feature processor (from transcription embeddings)
        self.text_encoder = tf.keras.Sequential([
            layers.Dense(512, activation='gelu'),
            layers.BatchNormalization(),
            layers.Dropout(dropout_rate),
            layers.Dense(d_model, activation='gelu'),
            layers.BatchNormalization(),
            layers.Dropout(dropout_rate * 0.7),
        ], name='text_encoder')
        
        # Sound classification processor (from YAMNet scores)
        self.sound_encoder = tf.keras.Sequential([
            layers.Dense(256, activation='gelu'),
            layers.BatchNormalization(),
            layers.Dropout(dropout_rate),
            layers.Dense(d_model, activation='gelu'),
            layers.BatchNormalization(),
        ], name='sound_encoder')
        
        # Cross-modal attention
        self.cross_attention = layers.MultiHeadAttention(
            num_heads=8,
            key_dim=d_model // 8,
            dropout=dropout_rate,
            name='cross_attention'
        )
        
        # Attention pooling
        self.attention_weights = layers.Dense(1, activation='softmax')
        
        # Fusion layer
        self.fusion = tf.keras.Sequential([
            layers.Dense(512, activation='gelu'),
            layers.BatchNormalization(),
            layers.Dropout(dropout_rate),
            layers.Dense(256, activation='gelu'),
            layers.BatchNormalization(),
            layers.Dropout(dropout_rate * 0.7),
        ], name='fusion')
        
        # Output heads (multi-task learning)
        self.location_head = tf.keras.Sequential([
            layers.Dense(128, activation='gelu'),
            layers.Dropout(dropout_rate * 0.5),
            layers.Dense(num_locations, activation='softmax')
        ], name='location_head')
        
        self.situation_head = tf.keras.Sequential([
            layers.Dense(128, activation='gelu'),
            layers.Dropout(dropout_rate * 0.5),
            layers.Dense(num_situations, activation='softmax')
        ], name='situation_head')
        
        self.confidence_head = tf.keras.Sequential([
            layers.Dense(64, activation='gelu'),
            layers.Dense(1, activation='sigmoid')
        ], name='confidence_head')
        
        self.emergency_head = tf.keras.Sequential([
            layers.Dense(64, activation='gelu'),
            layers.Dense(1, activation='sigmoid')
        ], name='emergency_head')
        
    def call(self, inputs, training=False):
        """
        Forward pass.
        
        Args:
            inputs: Dictionary with keys:
                - 'mel_spectrogram': [batch, time, freq]
                - 'text_embedding': [batch, embed_dim]
                - 'sound_scores': [batch, num_classes]
            training: Whether in training mode
            
        Returns:
            Dictionary with predictions
        """
        # Handle different input formats
        if isinstance(inputs, dict):
            mel_spec = inputs.get('mel_spectrogram')
            text_embed = inputs.get('text_embedding')
            sound_scores = inputs.get('sound_scores')
        elif isinstance(inputs, (list, tuple)):
            mel_spec, text_embed, sound_scores = inputs
        else:
            # Single input (mel spectrogram only)
            mel_spec = inputs
            text_embed = None
            sound_scores = None
        
        # Encode audio
        audio_features = self.audio_encoder(mel_spec, training=training)
        
        # Encode text (if available)
        if text_embed is not None:
            text_features = self.text_encoder(text_embed, training=training)
        else:
            text_features = tf.zeros_like(audio_features)
        
        # Encode sound scores (if available)
        if sound_scores is not None:
            sound_features = self.sound_encoder(sound_scores, training=training)
        else:
            sound_features = tf.zeros_like(audio_features)
        
        # Stack features for attention
        all_features = tf.stack([audio_features, text_features, sound_features], axis=1)
        
        # Cross-modal attention
        attended = self.cross_attention(
            query=all_features,
            key=all_features,
            value=all_features,
            training=training
        )
        
        # Attention-weighted pooling
        attention_weights = tf.nn.softmax(
            self.attention_weights(attended),
            axis=1
        )
        pooled = tf.reduce_sum(attended * attention_weights, axis=1)
        
        # Fusion
        fused = self.fusion(pooled, training=training)
        
        # Multi-task outputs
        location_probs = self.location_head(fused, training=training)
        situation_probs = self.situation_head(fused, training=training)
        confidence = self.confidence_head(fused, training=training)
        emergency = self.emergency_head(fused, training=training)
        
        return {
            'location': location_probs,
            'situation': situation_probs,
            'confidence': tf.squeeze(confidence, axis=-1),
            'emergency': tf.squeeze(emergency, axis=-1)
        }
    
    def get_config(self):
        return {
            'num_locations': self.num_locations,
            'num_situations': self.num_situations,
            'd_model': self.d_model
        }
    
    @classmethod
    def from_config(cls, config):
        return cls(**config)


# ==============================
# 🏋️ TRAINER CLASS
# ==============================
class SceneClassifierTrainer:
    """Training wrapper for AuralisSceneClassifier"""
    
    def __init__(
        self,
        model: AuralisSceneClassifier = None,
        model_path: str = None
    ):
        if model is not None:
            self.model = model
        elif model_path is not None:
            self.model = tf.keras.models.load_model(model_path)
        else:
            self.model = AuralisSceneClassifier()
            
        self.history = None
        
    def compile_model(
        self,
        learning_rate: float = None,
        location_weight: float = 1.0,
        situation_weight: float = 1.0,
        emergency_weight: float = 2.0
    ):
        """Compile model with multi-task loss"""
        
        learning_rate = learning_rate or config.training.learning_rate
        
        self.model.compile(
            optimizer=AdamW(
                learning_rate=learning_rate,
                weight_decay=config.training.weight_decay
            ),
            loss={
                'location': 'categorical_crossentropy',
                'situation': 'categorical_crossentropy',
                'confidence': 'mse',
                'emergency': 'binary_crossentropy'
            },
            loss_weights={
                'location': location_weight,
                'situation': situation_weight,
                'confidence': 0.5,
                'emergency': emergency_weight
            },
            metrics={
                'location': [
                    'accuracy',
                    tf.keras.metrics.TopKCategoricalAccuracy(k=3, name='top3_accuracy')
                ],
                'situation': [
                    'accuracy',
                    tf.keras.metrics.TopKCategoricalAccuracy(k=3, name='top3_accuracy')
                ],
                'confidence': ['mae'],
                'emergency': ['accuracy', tf.keras.metrics.AUC(name='auc')]
            }
        )
        
    def train(
        self,
        train_dataset,
        val_dataset,
        epochs: int = None,
        callbacks: list = None
    ):
        """Train the model"""
        
        epochs = epochs or config.training.epochs
        
        # Default callbacks
        if callbacks is None:
            callbacks = self._get_default_callbacks()
        
        self.history = self.model.fit(
            train_dataset,
            validation_data=val_dataset,
            epochs=epochs,
            callbacks=callbacks
        )
        
        return self.history
    
    def _get_default_callbacks(self):
        """Get default training callbacks"""
        return [
            tf.keras.callbacks.EarlyStopping(
                monitor='val_loss',
                patience=config.training.patience,
                restore_best_weights=True,
                min_delta=config.training.min_delta
            ),
            tf.keras.callbacks.ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.5,
                patience=config.training.patience // 2,
                min_lr=config.training.min_learning_rate
            ),
            tf.keras.callbacks.ModelCheckpoint(
                str(config.weights_dir / 'auralis_best.keras'),
                monitor='val_location_accuracy',
                save_best_only=True,
                mode='max'
            ),
            tf.keras.callbacks.TensorBoard(
                log_dir=str(config.logs_dir / 'tensorboard'),
                histogram_freq=1
            ),
            tf.keras.callbacks.CSVLogger(
                str(config.logs_dir / 'training_log.csv')
            )
        ]
    
    def evaluate(self, test_dataset):
        """Evaluate model on test set"""
        return self.model.evaluate(test_dataset, return_dict=True)
    
    def save(self, path: str = None):
        """Save model"""
        path = path or str(config.weights_dir / 'auralis_scene_classifier.keras')
        self.model.save(path)
        print(f"✅ Model saved to: {path}")
    
    def load(self, path: str):
        """Load model"""
        self.model = tf.keras.models.load_model(path)
        print(f"✅ Model loaded from: {path}")


# ==============================
# 🧪 TESTING
# ==============================
if __name__ == "__main__":
    print("=" * 60)
    print("Testing AuralisSceneClassifier")
    print("=" * 60)
    
    # Create model
    model = AuralisSceneClassifier()
    
    # Create dummy input
    batch_size = 4
    time_steps = 100
    mel_bins = 80
    
    dummy_input = {
        'mel_spectrogram': tf.random.normal([batch_size, time_steps, mel_bins]),
        'text_embedding': tf.random.normal([batch_size, 768]),
        'sound_scores': tf.random.normal([batch_size, 521])
    }
    
    # Forward pass
    output = model(dummy_input, training=False)
    
    print(f"\nInput shapes:")
    print(f"  Mel spectrogram: {dummy_input['mel_spectrogram'].shape}")
    print(f"  Text embedding: {dummy_input['text_embedding'].shape}")
    print(f"  Sound scores: {dummy_input['sound_scores'].shape}")
    
    print(f"\nOutput shapes:")
    print(f"  Location: {output['location'].shape}")
    print(f"  Situation: {output['situation'].shape}")
    print(f"  Confidence: {output['confidence'].shape}")
    print(f"  Emergency: {output['emergency'].shape}")
    
    print(f"\nModel summary:")
    model.summary()
    
    print(f"\nTotal parameters: {model.count_params():,}")
    print("=" * 60)