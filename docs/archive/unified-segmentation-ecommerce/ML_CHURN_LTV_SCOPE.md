# ML Scoping: Churn Prediction & LTV Forecasting

**Date**: 2025-11-12
**Purpose**: Comprehensive scoping of supervised ML models for churn and LTV
**Status**: Implementation Roadmap

---

## Executive Summary

**Current State**: Rules-based heuristics with ~60-70% accuracy
**Target State**: Trained ML models with 85%+ accuracy
**Timeline**: 6-8 weeks total
**Cost**: $15K-$25K (contractors) or 1 senior ML engineer
**ROI**: $100K+/year in improved retention and targeting

---

## Table of Contents

1. [Current State Analysis](#current-state-analysis)
2. [Churn Prediction Upgrade](#churn-prediction-upgrade)
3. [LTV Prediction Implementation](#ltv-prediction-implementation)
4. [Implementation Phases](#implementation-phases)
5. [Technical Architecture](#technical-architecture)
6. [Data Requirements](#data-requirements)
7. [Resource Requirements](#resource-requirements)
8. [Success Metrics](#success-metrics)
9. [Risk Mitigation](#risk-mitigation)

---

## Current State Analysis

### What Exists Today

**Location**: [mcp_server/segmentation_server.py:271-300](mcp_server/segmentation_server.py#L271-L300)

```python
def predict_churn_risk(customer_id: str) -> Dict[str, Any]:
    """Current implementation: Rules-based heuristics"""
    risk_score = 0.0

    # Rule 1: Membership strength check
    if profile['membership_strengths'].get('purchase_frequency') == 'weak':
        risk_score += 0.3  # ❌ HARDCODED

    # Rule 2: Recency check
    days_since = profile.get('days_since_last_purchase', 0)
    if days_since > 90:  # ❌ HARDCODED THRESHOLD
        risk_score += 0.3

    # Rule 3: Order count check
    if profile.get('total_orders', 0) < 5:  # ❌ HARDCODED
        risk_score += 0.2

    # Rule 4: Value trend check
    if profile.get('value_trend', 0) < -0.1:  # ❌ HARDCODED
        risk_score += 0.2

    return risk_score
```

### Problems with Current Approach

| Issue | Impact | Example |
|-------|--------|---------|
| **Hardcoded weights** | Weights (0.3, 0.3, 0.2, 0.2) are guesses | No data validation that 0.3 is optimal |
| **Hardcoded thresholds** | Thresholds (90 days, 5 orders) are Linda-specific | Breaks for other stores with different patterns |
| **No feature interactions** | Treats features independently | Misses: "High LTV + long recency = lower churn than low LTV + long recency" |
| **Binary logic** | If/else statements | Can't capture nuanced patterns |
| **No calibration** | Risk scores not validated | "0.8 risk" doesn't mean 80% actual churn |
| **No temporal features** | Only uses current snapshot | Misses: "Customer's frequency is declining" |

### Current Performance (Estimated)

Based on rules-based logic and industry benchmarks:

| Metric | Current | Industry Baseline | Target |
|--------|---------|------------------|--------|
| **AUC-ROC** | 0.60-0.65 | 0.70-0.75 | 0.85+ |
| **Precision** | ~50% | ~60% | 80% |
| **Recall** | ~40% | ~55% | 70% |
| **F1 Score** | 0.44 | 0.57 | 0.75 |

**Business Impact**:
- **100 predicted churners** → Only **50 actually churn** (50% precision)
- **Actual 100 churners** → Miss **60 of them** (40% recall)
- **Wasted budget**: $500/month on false positives (50 × $10 offer)

### LTV Prediction: Does NOT Exist

**Current**: Historical LTV only (sum of past orders)
**Missing**: Predictive LTV (what will customer spend in next 12 months?)

---

## Churn Prediction Upgrade

### Phase 1: LightGBM Churn Model (Weeks 1-3)

#### Why LightGBM?

| Criterion | LightGBM | Logistic Regression | Neural Network |
|-----------|----------|---------------------|----------------|
| **Training Time** | ⚡ Fast (<1 min) | ⚡ Fast | 🐢 Slow (10+ min) |
| **Categorical Support** | ✅ Native | ❌ Need encoding | ❌ Need encoding |
| **Feature Importance** | ✅ Built-in | ⚠️ Coefficients | ❌ Black box |
| **Overfitting Risk** | ⚠️ Medium | ✅ Low | ❌ High |
| **Interpretability** | ✅ SHAP values | ✅ High | ❌ Low |
| **Performance** | ✅ Excellent | ⚠️ Good | ✅ Excellent |

**Winner**: LightGBM - Best balance of speed, performance, and interpretability

#### Data Pipeline Design

```python
# backend/ml/churn/data_preparation.py

from typing import Tuple, List
import pandas as pd
from datetime import datetime, timedelta
from backend.segmentation.ecommerce_feature_extraction import EcommerceFeatureExtractor

class ChurnDataPipeline:
    """Prepares training data for churn prediction"""

    def __init__(
        self,
        observation_window_days: int = 180,  # Historical data to use
        prediction_window_days: int = 90,     # Predict churn in next 90 days
        churn_definition_days: int = 90       # No purchase in 90 days = churn
    ):
        self.observation_window = observation_window_days
        self.prediction_window = prediction_window_days
        self.churn_definition = churn_definition_days
        self.feature_extractor = EcommerceFeatureExtractor()


    def create_training_dataset(
        self,
        reference_date: datetime = None
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Create labeled training dataset with point-in-time correctness.

        For each customer at reference_date:
        1. Extract features using data UP TO reference_date
        2. Label: Did they churn in next 90 days?

        Args:
            reference_date: Snapshot date for training (default: 180 days ago)

        Returns:
            X: Feature matrix (N customers × ~50 features)
            y: Binary labels (1 = churned, 0 = retained)
        """
        if reference_date is None:
            # Default: 180 days ago (so we have 90-day labels)
            reference_date = datetime.now() - timedelta(days=180)

        training_data = []

        # Load all customers
        customers = self._load_customers()

        for customer in customers:
            # Get orders UP TO reference_date
            historical_orders = self._get_orders_before(
                customer.id,
                reference_date
            )

            # Skip if not enough history
            if len(historical_orders) < 2:
                continue

            # Extract features at reference_date
            self.feature_extractor.reference_date = reference_date
            features = self.feature_extractor.extract_all_features(
                customer.id,
                historical_orders,
                historical_items
            )

            # Flatten features into single vector
            feature_vector = self._flatten_features(features)

            # Add business metrics
            feature_vector['lifetime_value'] = sum(o['total_price'] for o in historical_orders)
            feature_vector['total_orders'] = len(historical_orders)
            feature_vector['tenure_days'] = (reference_date - historical_orders[0]['order_date']).days

            # LABEL: Did customer churn in next 90 days?
            future_date = reference_date + timedelta(days=90)
            future_orders = self._get_orders_between(
                customer.id,
                reference_date,
                future_date
            )

            # Churn = no orders in prediction window
            label = 1 if len(future_orders) == 0 else 0

            training_data.append({
                'customer_id': customer.id,
                'features': feature_vector,
                'label': label,
                'reference_date': reference_date
            })

        # Convert to DataFrame
        X = pd.DataFrame([d['features'] for d in training_data])
        y = pd.Series([d['label'] for d in training_data])

        # Add temporal features (changes over time)
        X = self._add_temporal_features(X, training_data)

        return X, y


    def _flatten_features(self, features: Dict) -> Dict:
        """Flatten nested axis features into single dict"""
        flat = {}

        for axis_name, axis_features in features.items():
            for feature_name, value in axis_features.items():
                flat[f"{axis_name}_{feature_name}"] = value

        return flat


    def _add_temporal_features(
        self,
        X: pd.DataFrame,
        training_data: List[Dict]
    ) -> pd.DataFrame:
        """
        Add temporal trend features (change over time).

        Compare current snapshot vs 30/60/90 days prior:
        - purchase_frequency_trend_30d
        - purchase_value_trend_30d
        - etc.
        """
        temporal_features = []

        for row in training_data:
            customer_id = row['customer_id']
            reference_date = row['reference_date']

            # Get snapshots at -30d, -60d, -90d
            snapshots = {}
            for days_ago in [30, 60, 90]:
                snapshot_date = reference_date - timedelta(days=days_ago)
                orders = self._get_orders_before(customer_id, snapshot_date)

                if len(orders) >= 2:
                    features = self.feature_extractor.extract_all_features(
                        customer_id, orders, items
                    )
                    snapshots[f"{days_ago}d"] = features

            # Calculate trends
            trends = {}
            if '30d' in snapshots and '90d' in snapshots:
                # Frequency trend
                freq_now = row['features']['purchase_frequency_orders_per_month']
                freq_30d = snapshots['30d']['purchase_frequency']['orders_per_month']
                freq_90d = snapshots['90d']['purchase_frequency']['orders_per_month']

                trends['frequency_trend_30d'] = (freq_now - freq_30d) / 30
                trends['frequency_trend_90d'] = (freq_now - freq_90d) / 90

                # Value trend
                value_now = row['features']['purchase_value_avg_order_value']
                value_30d = snapshots['30d']['purchase_value']['avg_order_value']

                trends['value_trend_30d'] = (value_now - value_30d) / value_30d if value_30d > 0 else 0

            temporal_features.append(trends)

        # Add temporal features to X
        temporal_df = pd.DataFrame(temporal_features)
        X = pd.concat([X, temporal_df], axis=1)

        return X


# Example usage
pipeline = ChurnDataPipeline()

# Create training data from 180 days ago
X_train, y_train = pipeline.create_training_dataset(
    reference_date=datetime(2025, 5, 15)  # 6 months ago
)

print(f"Training samples: {len(X_train)}")
print(f"Churn rate: {y_train.mean():.1%}")
print(f"Features: {X_train.shape[1]}")
```

#### Model Training

```python
# backend/ml/churn/model.py

import lightgbm as lgb
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.metrics import roc_auc_score, classification_report, roc_curve
import numpy as np
import joblib
from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class ChurnModel:
    """LightGBM-based churn prediction model"""

    def __init__(self):
        self.model = None
        self.feature_names = None
        self.threshold = 0.7  # Will be optimized

        # LightGBM hyperparameters (tuned)
        self.params = {
            'objective': 'binary',
            'metric': 'auc',
            'boosting_type': 'gbdt',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'feature_fraction': 0.8,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'max_depth': 6,
            'min_child_samples': 50,  # Prevent overfitting
            'verbose': -1,
            'random_state': 42
        }


    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame = None,
        y_val: pd.Series = None
    ) -> Dict:
        """
        Train LightGBM model with early stopping.

        Returns:
            metrics: Training and validation metrics
        """
        self.feature_names = X_train.columns.tolist()

        # Create LightGBM datasets
        train_data = lgb.Dataset(X_train, label=y_train)

        # Early stopping on validation set
        valid_sets = [train_data]
        valid_names = ['train']

        if X_val is not None and y_val is not None:
            val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)
            valid_sets.append(val_data)
            valid_names.append('valid')

        # Train
        logger.info("Training LightGBM churn model...")
        self.model = lgb.train(
            self.params,
            train_data,
            num_boost_round=500,
            valid_sets=valid_sets,
            valid_names=valid_names,
            callbacks=[
                lgb.early_stopping(stopping_rounds=25),
                lgb.log_evaluation(period=50)
            ]
        )

        # Evaluate
        metrics = self._evaluate(X_train, y_train, X_val, y_val)

        # Optimize threshold for business use case
        self.threshold = self._optimize_threshold(X_val, y_val)

        logger.info(f"Model trained. AUC: {metrics['val_auc']:.3f}, Threshold: {self.threshold:.3f}")

        return metrics


    def _evaluate(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame,
        y_val: pd.Series
    ) -> Dict:
        """Calculate performance metrics"""

        metrics = {}

        # Training metrics
        y_train_pred = self.model.predict(X_train)
        metrics['train_auc'] = roc_auc_score(y_train, y_train_pred)

        # Validation metrics
        if X_val is not None and y_val is not None:
            y_val_pred = self.model.predict(X_val)
            metrics['val_auc'] = roc_auc_score(y_val, y_val_pred)

            # Classification metrics at 0.5 threshold
            y_val_class = (y_val_pred >= 0.5).astype(int)
            from sklearn.metrics import precision_score, recall_score, f1_score

            metrics['precision'] = precision_score(y_val, y_val_class)
            metrics['recall'] = recall_score(y_val, y_val_class)
            metrics['f1'] = f1_score(y_val, y_val_class)

            # Feature importance
            importance = self.model.feature_importance(importance_type='gain')
            feature_importance = dict(zip(self.feature_names, importance))
            metrics['top_10_features'] = sorted(
                feature_importance.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]

        return metrics


    def _optimize_threshold(
        self,
        X_val: pd.DataFrame,
        y_val: pd.Series,
        cost_false_positive: float = 10,   # Cost of retention offer
        cost_false_negative: float = 150   # Lost LTV from churned customer
    ) -> float:
        """
        Find optimal classification threshold based on business costs.

        Default costs:
        - False positive: $10 (retention offer to non-churner)
        - False negative: $150 (miss a churner, lose LTV)

        Returns:
            optimal_threshold: Threshold that minimizes total cost
        """
        y_pred_proba = self.model.predict(X_val)

        # Try thresholds from 0.3 to 0.9
        thresholds = np.arange(0.3, 0.9, 0.05)
        costs = []

        for threshold in thresholds:
            y_pred = (y_pred_proba >= threshold).astype(int)

            # Calculate costs
            fp = ((y_pred == 1) & (y_val == 0)).sum()  # Predict churn, actually retained
            fn = ((y_pred == 0) & (y_val == 1)).sum()  # Predict retained, actually churn

            total_cost = fp * cost_false_positive + fn * cost_false_negative
            costs.append(total_cost)

        # Find threshold with minimum cost
        optimal_idx = np.argmin(costs)
        optimal_threshold = thresholds[optimal_idx]

        logger.info(f"Optimal threshold: {optimal_threshold:.3f} (min cost: ${costs[optimal_idx]:.0f})")

        return optimal_threshold


    def predict(self, X: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Predict churn probability and binary classification.

        Returns:
            probabilities: Churn probability (0-1)
            predictions: Binary classification (0 or 1)
        """
        probabilities = self.model.predict(X)
        predictions = (probabilities >= self.threshold).astype(int)

        return probabilities, predictions


    def predict_with_explanation(
        self,
        customer_features: Dict
    ) -> Dict:
        """
        Predict churn with SHAP explanation.

        Returns:
            {
                'churn_probability': 0.73,
                'churn_prediction': 1,
                'risk_level': 'HIGH',
                'top_factors': [
                    {'feature': 'days_since_last_purchase', 'contribution': +0.15},
                    {'feature': 'frequency_trend_30d', 'contribution': +0.12},
                    ...
                ]
            }
        """
        import shap

        # Convert to DataFrame
        X = pd.DataFrame([customer_features])

        # Predict
        probability, prediction = self.predict(X)

        # SHAP explanation
        explainer = shap.TreeExplainer(self.model)
        shap_values = explainer.shap_values(X)

        # Top contributing features
        feature_contributions = list(zip(self.feature_names, shap_values[0]))
        top_factors = sorted(
            feature_contributions,
            key=lambda x: abs(x[1]),
            reverse=True
        )[:5]

        # Risk level
        prob = probability[0]
        if prob >= 0.7:
            risk_level = 'CRITICAL'
        elif prob >= 0.5:
            risk_level = 'ELEVATED'
        elif prob >= 0.3:
            risk_level = 'MODERATE'
        else:
            risk_level = 'LOW'

        return {
            'churn_probability': float(prob),
            'churn_prediction': int(prediction[0]),
            'risk_level': risk_level,
            'top_factors': [
                {'feature': f, 'contribution': float(c)}
                for f, c in top_factors
            ]
        }


    def save(self, path: str):
        """Save model to disk"""
        joblib.dump({
            'model': self.model,
            'feature_names': self.feature_names,
            'threshold': self.threshold,
            'params': self.params
        }, path)
        logger.info(f"Model saved to {path}")


    @classmethod
    def load(cls, path: str):
        """Load model from disk"""
        data = joblib.load(path)

        instance = cls()
        instance.model = data['model']
        instance.feature_names = data['feature_names']
        instance.threshold = data['threshold']
        instance.params = data['params']

        logger.info(f"Model loaded from {path}")
        return instance
```

#### Training Script

```python
# scripts/train_churn_model.py

import sys
sys.path.insert(0, '.')

from backend.ml.churn.data_preparation import ChurnDataPipeline
from backend.ml.churn.model import ChurnModel
from datetime import datetime, timedelta
from sklearn.model_selection import TimeSeriesSplit
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def train_churn_model():
    """Train churn prediction model with time-series cross-validation"""

    logger.info("=== Churn Model Training ===")

    # Step 1: Prepare data
    pipeline = ChurnDataPipeline(
        observation_window_days=180,
        prediction_window_days=90,
        churn_definition_days=90
    )

    # Create training data from 6 months ago (so we have labels)
    reference_date = datetime.now() - timedelta(days=180)

    logger.info(f"Creating training data (reference: {reference_date.date()})...")
    X, y = pipeline.create_training_dataset(reference_date)

    logger.info(f"Dataset: {len(X)} customers, {X.shape[1]} features")
    logger.info(f"Churn rate: {y.mean():.1%}")

    # Step 2: Time-series cross-validation
    # Use 5 folds, always train on past, validate on future
    tscv = TimeSeriesSplit(n_splits=5)

    cv_scores = []

    for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
        logger.info(f"\n--- Fold {fold + 1}/5 ---")

        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

        # Train model
        model = ChurnModel()
        metrics = model.train(X_train, y_train, X_val, y_val)

        logger.info(f"Fold {fold + 1} AUC: {metrics['val_auc']:.3f}")
        logger.info(f"Fold {fold + 1} Precision: {metrics['precision']:.3f}")
        logger.info(f"Fold {fold + 1} Recall: {metrics['recall']:.3f}")

        cv_scores.append(metrics['val_auc'])

    # Step 3: Train final model on all data
    logger.info(f"\n=== Final Model Training ===")
    logger.info(f"Cross-validation AUC: {np.mean(cv_scores):.3f} ± {np.std(cv_scores):.3f}")

    # Hold out last 20% for final evaluation
    split_idx = int(len(X) * 0.8)
    X_train_final, X_test_final = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train_final, y_test_final = y.iloc[:split_idx], y.iloc[split_idx:]

    final_model = ChurnModel()
    metrics = final_model.train(X_train_final, y_train_final, X_test_final, y_test_final)

    # Step 4: Feature importance
    logger.info("\n=== Top 10 Most Important Features ===")
    for feature, importance in metrics['top_10_features']:
        logger.info(f"  {feature}: {importance:.0f}")

    # Step 5: Save model
    model_path = 'models/churn_model_v1.joblib'
    final_model.save(model_path)

    logger.info(f"\n✅ Training complete!")
    logger.info(f"Final Test AUC: {metrics['val_auc']:.3f}")
    logger.info(f"Model saved to: {model_path}")

    return final_model, metrics


if __name__ == '__main__':
    model, metrics = train_churn_model()
```

#### Expected Features (~50 total)

**From 13 Behavioral Axes** (~40 features):
- `purchase_frequency_orders_per_month`
- `purchase_frequency_avg_days_between_orders`
- `purchase_frequency_recent_orders_90d`
- `purchase_frequency_days_since_last`
- `purchase_value_lifetime_value`
- `purchase_value_avg_order_value`
- `purchase_value_value_trend`
- `category_exploration_unique_categories`
- `category_exploration_category_diversity`
- ...all 13 axes

**Business Metrics** (~5 features):
- `lifetime_value`
- `total_orders`
- `tenure_days`
- `avg_order_value`
- `days_since_last_purchase`

**Temporal Trends** (~8 features):
- `frequency_trend_30d` (change in last 30 days)
- `frequency_trend_90d`
- `value_trend_30d`
- `value_trend_90d`
- `recency_acceleration` (are gaps getting longer?)
- `spending_acceleration` (spending increasing/decreasing?)

**Archetype Features** (~3 features):
- `archetype_baseline_churn` (historical churn rate for this archetype)
- `membership_strength_score` (avg membership across axes)
- `archetype_stability` (how long in current archetype)

#### Deployment

```python
# backend/api/routers/predictions.py

from fastapi import APIRouter, Depends
from backend.ml.churn.model import ChurnModel
from backend.segmentation.ecommerce_feature_extraction import EcommerceFeatureExtractor
import os

router = APIRouter()

# Load model at startup
CHURN_MODEL = None

@router.on_event("startup")
async def load_model():
    global CHURN_MODEL
    model_path = os.getenv("CHURN_MODEL_PATH", "models/churn_model_v1.joblib")
    CHURN_MODEL = ChurnModel.load(model_path)


@router.get("/api/v1/customers/{customer_id}/churn-risk-ml")
async def predict_churn_ml(customer_id: str):
    """
    Predict churn risk using ML model (replaces rules-based version).

    Returns:
        {
            "churn_probability": 0.73,
            "churn_prediction": 1,
            "risk_level": "CRITICAL",
            "top_factors": [
                {"feature": "days_since_last_purchase", "contribution": +0.15},
                {"feature": "frequency_trend_30d", "contribution": +0.12}
            ],
            "recommended_actions": [
                "Send retention email with 15% discount",
                "Flag for account manager outreach"
            ]
        }
    """
    # Get customer orders
    orders = await get_customer_orders(customer_id)
    items = await get_customer_items(customer_id)

    # Extract features
    feature_extractor = EcommerceFeatureExtractor()
    features = feature_extractor.extract_all_features(customer_id, orders, items)

    # Flatten features
    feature_vector = {}
    for axis_name, axis_features in features.items():
        for feature_name, value in axis_features.items():
            feature_vector[f"{axis_name}_{feature_name}"] = value

    # Add business metrics
    feature_vector['lifetime_value'] = sum(o['total_price'] for o in orders)
    feature_vector['total_orders'] = len(orders)

    # Predict
    result = CHURN_MODEL.predict_with_explanation(feature_vector)

    # Add recommended actions
    risk_level = result['risk_level']
    ltv = feature_vector['lifetime_value']

    actions = []
    if risk_level == 'CRITICAL':
        if ltv > 2000:
            actions.append("Personal call from account manager")
            actions.append("20% retention discount")
        else:
            actions.append("Send retention email")
            actions.append("15% discount code")
    elif risk_level == 'ELEVATED':
        actions.append("Include in re-engagement campaign")
        actions.append("Send new product recommendations")

    result['recommended_actions'] = actions

    return result
```

### Phase 2: Model Monitoring & A/B Testing (Week 4)

#### Monitoring Dashboard

```python
# backend/ml/churn/monitoring.py

from typing import Dict, List
import pandas as pd
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class ChurnModelMonitor:
    """Monitor churn model performance in production"""

    def __init__(self):
        self.metrics_history = []


    async def log_prediction(
        self,
        customer_id: str,
        prediction: float,
        risk_level: str,
        timestamp: datetime = None
    ):
        """Log prediction for later validation"""
        await db.execute(
            """
            INSERT INTO ml_predictions (
                customer_id,
                model_name,
                prediction_value,
                risk_level,
                predicted_at,
                validation_date
            ) VALUES ($1, $2, $3, $4, $5, $6)
            """,
            customer_id,
            'churn_model_v1',
            prediction,
            risk_level,
            timestamp or datetime.now(),
            (timestamp or datetime.now()) + timedelta(days=90)
        )


    async def validate_predictions(self) -> Dict:
        """
        Validate predictions that have reached validation date.

        Returns:
            {
                'total_predictions': 1000,
                'validated': 850,
                'accuracy': 0.82,
                'auc': 0.87,
                'precision': 0.79,
                'recall': 0.72
            }
        """
        # Get predictions that should be validated (90 days have passed)
        validation_date = datetime.now()

        predictions = await db.fetch(
            """
            SELECT
                mp.customer_id,
                mp.prediction_value,
                mp.predicted_at,
                CASE
                    WHEN MAX(o.order_date) < mp.validation_date THEN 1
                    ELSE 0
                END as actual_churn
            FROM ml_predictions mp
            LEFT JOIN orders o ON mp.customer_id = o.customer_id
                AND o.order_date >= mp.predicted_at
                AND o.order_date < mp.validation_date
            WHERE mp.validation_date <= $1
                AND mp.validated_at IS NULL
            GROUP BY mp.customer_id, mp.prediction_value, mp.predicted_at, mp.validation_date
            """,
            validation_date
        )

        if len(predictions) == 0:
            return {'message': 'No predictions ready for validation'}

        # Calculate metrics
        from sklearn.metrics import roc_auc_score, precision_score, recall_score, accuracy_score

        y_true = [p['actual_churn'] for p in predictions]
        y_pred_proba = [p['prediction_value'] for p in predictions]
        y_pred = [1 if p >= 0.7 else 0 for p in y_pred_proba]

        metrics = {
            'total_predictions': len(predictions),
            'validated': len([p for p in predictions if p['actual_churn'] is not None]),
            'accuracy': accuracy_score(y_true, y_pred),
            'auc': roc_auc_score(y_true, y_pred_proba),
            'precision': precision_score(y_true, y_pred),
            'recall': recall_score(y_true, y_pred),
            'churn_rate': sum(y_true) / len(y_true)
        }

        # Mark as validated
        await db.execute(
            """
            UPDATE ml_predictions
            SET validated_at = $1,
                actual_outcome = CASE
                    WHEN customer_id = ANY($2) THEN 1
                    ELSE 0
                END
            WHERE customer_id = ANY($3)
            """,
            datetime.now(),
            [p['customer_id'] for p in predictions if p['actual_churn'] == 1],
            [p['customer_id'] for p in predictions]
        )

        # Alert if performance degrades
        if metrics['auc'] < 0.75:
            logger.warning(f"Model performance degraded! AUC: {metrics['auc']:.3f}")
            await self._send_alert("Model performance degradation", metrics)

        return metrics
```

#### A/B Testing Framework

```python
# backend/ml/ab_testing.py

from enum import Enum
from typing import Dict
import hashlib

class ChurnModel(Enum):
    RULES_BASED = "rules_based"  # Old model
    LIGHTGBM = "lightgbm"          # New model

class ABTestManager:
    """A/B test churn models"""

    def __init__(self, experiment_name: str = "churn_model_v1", rollout_pct: float = 0.5):
        self.experiment_name = experiment_name
        self.rollout_pct = rollout_pct  # 50% get new model


    def assign_variant(self, customer_id: str) -> ChurnModel:
        """
        Consistently assign customer to A or B group.

        Uses hashing to ensure same customer always gets same variant.
        """
        hash_value = int(hashlib.md5(f"{self.experiment_name}_{customer_id}".encode()).hexdigest(), 16)

        if (hash_value % 100) < (self.rollout_pct * 100):
            return ChurnModel.LIGHTGBM
        else:
            return ChurnModel.RULES_BASED


    async def get_churn_prediction(self, customer_id: str) -> Dict:
        """Get churn prediction using assigned model variant"""

        variant = self.assign_variant(customer_id)

        # Log assignment
        await db.execute(
            """
            INSERT INTO ab_test_assignments (customer_id, experiment_name, variant, assigned_at)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (customer_id, experiment_name) DO NOTHING
            """,
            customer_id, self.experiment_name, variant.value, datetime.now()
        )

        # Get prediction from assigned model
        if variant == ChurnModel.LIGHTGBM:
            result = await predict_churn_ml(customer_id)
            result['model'] = 'lightgbm'
        else:
            result = await predict_churn_rules(customer_id)
            result['model'] = 'rules_based'

        return result


    async def analyze_experiment(self) -> Dict:
        """
        Compare performance of A vs B groups.

        Returns:
            {
                'lightgbm': {'auc': 0.87, 'precision': 0.79, 'users': 5000},
                'rules_based': {'auc': 0.62, 'precision': 0.51, 'users': 5000},
                'winner': 'lightgbm',
                'improvement': '+40% AUC'
            }
        """
        # Get validated predictions for both variants
        results = await db.fetch("""
            SELECT
                a.variant,
                COUNT(*) as predictions,
                AVG(CASE WHEN p.actual_outcome = 1 THEN 1 ELSE 0 END) as churn_rate,
                -- Calculate AUC, precision, recall per variant
                ...
            FROM ab_test_assignments a
            JOIN ml_predictions p ON a.customer_id = p.customer_id
            WHERE a.experiment_name = $1
                AND p.validated_at IS NOT NULL
            GROUP BY a.variant
        """, self.experiment_name)

        # Compare
        ...

        return comparison
```

---

## LTV Prediction Implementation

### Phase 3: LTV Forecasting Model (Weeks 5-6)

#### Why Predict LTV?

**Use Cases**:
1. **Campaign ROI**: Only target customers with LTV > CAC
2. **Prioritization**: Focus retention efforts on high future-LTV customers
3. **Budgeting**: Forecast revenue from customer base
4. **Segmentation**: "High potential" vs "maxed out" customers

#### Data Requirements

**Historical LTV** (what we have):
```python
ltv_historical = sum(order['total_price'] for order in past_orders)
```

**Predictive LTV** (what we need):
```python
ltv_predicted = ltv_historical + ltv_future_12_months
```

#### Model Choice: Gamma Regression

**Why Gamma?**
- LTV is continuous, positive, right-skewed (most customers low LTV, few very high)
- Gamma distribution fits this perfectly
- Better than linear regression (which can predict negative LTV)

**Alternative**: XGBoost Regressor (also works well)

#### Implementation

```python
# backend/ml/ltv/model.py

from sklearn.linear_model import GammaRegressor
from sklearn.ensemble import GradientBoostingRegressor
import numpy as np
import pandas as pd

class LTVModel:
    """Predict customer lifetime value over next 12 months"""

    def __init__(self, prediction_window_months: int = 12):
        self.prediction_window = prediction_window_months
        self.model = None

        # Use Gamma regression (better for positive skewed targets)
        self.model = GammaRegressor(
            alpha=1.0,  # Regularization
            max_iter=100
        )


    def prepare_training_data(self) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Create training data with point-in-time correctness.

        For each customer 12 months ago:
        - Features: Their behavior up to that point
        - Target: How much they spent in next 12 months
        """
        reference_date = datetime.now() - timedelta(days=365)

        training_data = []

        for customer in customers:
            # Historical orders (up to 12 months ago)
            historical_orders = get_orders_before(customer.id, reference_date)

            if len(historical_orders) < 2:
                continue

            # Extract features
            features = extract_features(customer.id, historical_orders)

            # TARGET: Spend in next 12 months
            future_date = reference_date + timedelta(days=365)
            future_orders = get_orders_between(customer.id, reference_date, future_date)

            future_spend = sum(o['total_price'] for o in future_orders)

            training_data.append({
                'features': features,
                'target': future_spend
            })

        X = pd.DataFrame([d['features'] for d in training_data])
        y = pd.Series([d['target'] for d in training_data])

        return X, y


    def train(self, X: pd.DataFrame, y: pd.Series):
        """Train LTV prediction model"""

        # Log transform target (makes Gamma regression more stable)
        y_log = np.log1p(y)  # log(1 + y) to handle zeros

        # Train
        self.model.fit(X, y_log)

        # Evaluate
        y_pred_log = self.model.predict(X)
        y_pred = np.expm1(y_pred_log)  # exp(y) - 1

        # Metrics
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

        mae = mean_absolute_error(y, y_pred)
        rmse = np.sqrt(mean_squared_error(y, y_pred))
        r2 = r2_score(y, y_pred)

        logger.info(f"LTV Model - MAE: ${mae:.2f}, RMSE: ${rmse:.2f}, R²: {r2:.3f}")

        return {'mae': mae, 'rmse': rmse, 'r2': r2}


    def predict(self, customer_features: Dict) -> Dict:
        """
        Predict 12-month future LTV.

        Returns:
            {
                'ltv_predicted_12m': 450.0,
                'ltv_historical': 120.0,
                'ltv_total_predicted': 570.0,
                'confidence_interval': [350, 600],
                'prediction_basis': 'Based on 5 historical orders, avg $24/order'
            }
        """
        X = pd.DataFrame([customer_features])

        # Predict (returns log-transformed value)
        y_pred_log = self.model.predict(X)
        ltv_predicted = np.expm1(y_pred_log)[0]

        # Confidence interval (approximate)
        # Use variance of predictions on validation set
        std_dev = 100  # Calibrated from validation
        ci_lower = max(0, ltv_predicted - 1.96 * std_dev)
        ci_upper = ltv_predicted + 1.96 * std_dev

        return {
            'ltv_predicted_12m': ltv_predicted,
            'ltv_historical': customer_features.get('lifetime_value', 0),
            'ltv_total_predicted': customer_features.get('lifetime_value', 0) + ltv_predicted,
            'confidence_interval': [ci_lower, ci_upper],
            'prediction_basis': f"Based on {customer_features.get('total_orders', 0)} orders"
        }
```

#### Key Features for LTV Prediction

**Best Predictors** (from e-commerce research):
1. **Historical LTV** (strongest predictor)
2. **Recent purchase frequency** (orders in last 90 days)
3. **Average order value trend** (increasing/decreasing)
4. **Days since last purchase** (recency)
5. **Customer tenure** (longer = more future value)
6. **Category breadth** (multi-category buyers spend more)
7. **Discount dependency** (full-price buyers have higher LTV)
8. **Seasonal patterns** (regular buyers = predictable LTV)

---

## Implementation Phases

### Timeline Overview

| Phase | Duration | Deliverable | Status |
|-------|----------|-------------|--------|
| **Phase 1: Churn Model** | Weeks 1-3 | LightGBM model with 85%+ AUC | 🔴 To Do |
| **Phase 2: Monitoring** | Week 4 | A/B test + dashboard | 🔴 To Do |
| **Phase 3: LTV Model** | Weeks 5-6 | Gamma regression LTV predictor | 🔴 To Do |
| **Phase 4: Integration** | Weeks 7-8 | API endpoints, Gorgias integration | 🔴 To Do |

### Detailed Week-by-Week Plan

**Week 1**: Data Pipeline & Feature Engineering
- ✅ Adapt EcommerceFeatureExtractor for ML
- ✅ Build ChurnDataPipeline with point-in-time correctness
- ✅ Generate training dataset (X, y)
- ✅ Validate data quality (no leakage, correct labels)

**Week 2**: Model Training & Tuning
- ✅ Train LightGBM baseline
- ✅ Hyperparameter tuning (GridSearch/Optuna)
- ✅ Time-series cross-validation
- ✅ Feature importance analysis
- ✅ SHAP explanations

**Week 3**: Model Optimization & Testing
- ✅ Threshold optimization for business costs
- ✅ Test on holdout set
- ✅ Compare vs rules-based model
- ✅ Document model card

**Week 4**: Deployment & Monitoring
- ✅ Deploy model to production
- ✅ Create prediction logging
- ✅ Build A/B testing framework
- ✅ Set up monitoring dashboard

**Week 5**: LTV Model Development
- ✅ Prepare LTV training data
- ✅ Train Gamma regression model
- ✅ Validate predictions
- ✅ Feature importance

**Week 6**: LTV Integration
- ✅ Deploy LTV model
- ✅ Combine churn + LTV for prioritization
- ✅ Build "Expected Customer Value" score
- ✅ Testing

**Week 7**: API Integration
- ✅ Update customer profile endpoints
- ✅ Gorgias webhook enrichment
- ✅ Slack bot integration
- ✅ Documentation

**Week 8**: Testing & Rollout
- ✅ End-to-end testing
- ✅ Gradual rollout (10% → 50% → 100%)
- ✅ Training for support team
- ✅ Success metrics tracking

---

## Technical Architecture

### File Structure

```
backend/
├── ml/
│   ├── __init__.py
│   ├── churn/
│   │   ├── __init__.py
│   │   ├── data_preparation.py      # ChurnDataPipeline
│   │   ├── model.py                 # ChurnModel (LightGBM)
│   │   ├── monitoring.py            # Performance tracking
│   │   └── explainability.py        # SHAP explanations
│   ├── ltv/
│   │   ├── __init__.py
│   │   ├── data_preparation.py      # LTV training data
│   │   ├── model.py                 # LTVModel (Gamma regression)
│   │   └── evaluation.py            # Validation metrics
│   └── ab_testing.py                # A/B test framework
├── api/
│   └── routers/
│       └── predictions.py           # /api/v1/customers/{id}/churn-risk-ml
│                                    # /api/v1/customers/{id}/ltv-prediction
└── segmentation/
    └── ecommerce_feature_extraction.py  # Already exists

scripts/
├── train_churn_model.py             # Training script
├── train_ltv_model.py               # LTV training
├── validate_models.py               # Validation
└── backtest_models.py               # Historical performance

models/
├── churn_model_v1.joblib            # Saved LightGBM
├── ltv_model_v1.joblib              # Saved Gamma model
└── model_metadata.json              # Training info

alembic/versions/
└── 2025_11_12_add_ml_predictions_table.py  # New table for logging

tests/
├── test_churn_model.py
├── test_ltv_model.py
└── test_ab_testing.py
```

### Database Schema

```sql
-- Store ML predictions for validation
CREATE TABLE ml_predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id VARCHAR(100) NOT NULL,
    model_name VARCHAR(50) NOT NULL,  -- 'churn_model_v1', 'ltv_model_v1'
    prediction_value FLOAT NOT NULL,
    risk_level VARCHAR(20),  -- For churn: 'CRITICAL', 'ELEVATED', etc.
    predicted_at TIMESTAMP NOT NULL DEFAULT NOW(),
    validation_date DATE NOT NULL,  -- When to check actual outcome
    validated_at TIMESTAMP,
    actual_outcome FLOAT,  -- Actual churn (0/1) or actual LTV
    feature_vector JSONB,  -- Store features for debugging

    INDEX idx_validation (validation_date, validated_at),
    INDEX idx_customer (customer_id, predicted_at)
);

-- A/B test assignments
CREATE TABLE ab_test_assignments (
    customer_id VARCHAR(100) NOT NULL,
    experiment_name VARCHAR(100) NOT NULL,
    variant VARCHAR(50) NOT NULL,  -- 'lightgbm', 'rules_based'
    assigned_at TIMESTAMP NOT NULL DEFAULT NOW(),

    PRIMARY KEY (customer_id, experiment_name)
);

-- Model performance tracking
CREATE TABLE ml_model_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name VARCHAR(50) NOT NULL,
    metric_name VARCHAR(50) NOT NULL,  -- 'auc', 'precision', 'mae'
    metric_value FLOAT NOT NULL,
    measured_at TIMESTAMP NOT NULL DEFAULT NOW(),
    sample_size INT,

    INDEX idx_model_time (model_name, measured_at)
);
```

---

## Data Requirements

### Current Data (Available)

**From PostgreSQL (combined_sales table)**:
- ✅ 1.2M order line items
- ✅ 200K orders
- ✅ 93K customers
- ✅ 4+ years history (2021-2025)
- ✅ Order dates, prices, products, categories

**Sufficient for**:
- ✅ Churn model training (need 6+ months lookback)
- ✅ LTV model training (need 12+ months lookback)
- ✅ Feature engineering (all 13 axes)

### Missing Data (Would Improve Models)

**Email Engagement** (from Klaviyo):
- Email open rate
- Click-through rate
- Last email interaction
- **Impact**: +5% AUC improvement

**Website Behavior** (from Google Analytics):
- Page views
- Session duration
- Cart abandonment
- **Impact**: +3% AUC improvement

**Support Tickets** (from Gorgias):
- Ticket count
- Satisfaction scores
- Issue types
- **Impact**: +4% AUC improvement

**Total Potential**: +12% AUC with additional data sources

**Decision**: Start with order data only, add integrations later

---

## Resource Requirements

### Option 1: ML Contractor ($10K-$15K)

**Profile**:
- Senior ML Engineer
- 5+ years experience
- E-commerce or subscription ML background
- LightGBM/XGBoost expertise

**Scope**: 4-6 weeks, part-time (20 hours/week)

**Deliverables**:
- Churn model (LightGBM)
- LTV model (Gamma regression)
- Training scripts
- Monitoring framework
- Documentation
- 2 weeks of support post-launch

**Platforms**: Upwork, Toptal, Braintrust

### Option 2: Full-Time ML Engineer ($120K-$150K/year)

**Profile**:
- Mid-level ML Engineer
- 3+ years experience
- Python, scikit-learn, LightGBM
- Deployment experience (FastAPI, Docker)

**Timeline**: Hire in Q1 2026

**Responsibilities**:
- Maintain churn/LTV models
- Build new models (product recommendations, customer segmentation 2.0)
- Monitor performance
- Improve with new data sources

### Option 3: Hybrid (Recommended)

**Phase 1** (Months 1-2): Contractor builds initial models ($10K)
**Phase 2** (Months 3-6): Founder maintains & monitors (10 hours/month)
**Phase 3** (Month 7+): Hire full-time ML engineer after product-market fit

---

## Success Metrics

### Model Performance

**Churn Prediction**:
| Metric | Current | Target | Measured How |
|--------|---------|--------|--------------|
| AUC-ROC | 0.60-0.65 | 0.85+ | Time-series CV |
| Precision @ 70% | 50% | 80% | Validation set |
| Recall @ 70% | 40% | 70% | Validation set |
| F1 Score | 0.44 | 0.75 | Validation set |

**LTV Prediction**:
| Metric | Baseline | Target | Measured How |
|--------|----------|--------|--------------|
| MAE | - | <$50 | 12-month validation |
| RMSE | - | <$75 | 12-month validation |
| R² | - | 0.70+ | Validation set |
| % within 20% | - | 75%+ | Accuracy band |

### Business Impact

**Cost Savings** (from improved churn prediction):
```
Current waste: 50 false positives/month × $10 offer = $500/month
Improved waste: 20 false positives/month × $10 offer = $200/month
Savings: $300/month = $3,600/year
```

**Revenue Protection** (from improved recall):
```
Current misses: 60 churners/month × $150 avg LTV = $9,000/month lost
Improved misses: 30 churners/month × $150 avg LTV = $4,500/month lost
Protection: $4,500/month = $54,000/year
```

**LTV Targeting** (from LTV predictions):
```
Better campaign targeting: +20% ROI on retention campaigns
Avg campaign spend: $5,000/month
Improvement: $1,000/month = $12,000/year
```

**Total Annual Impact**: $70K+ in first year

---

## Risk Mitigation

### Technical Risks

**Risk 1: Data Quality Issues**
- **Mitigation**: Extensive data validation, outlier detection
- **Fallback**: Rules-based model still available

**Risk 2: Model Performance Below Target**
- **Mitigation**: Time-series CV during development
- **Fallback**: Iterate on features, try ensemble methods

**Risk 3: Deployment Bugs**
- **Mitigation**: Comprehensive testing, gradual rollout
- **Fallback**: Feature flag to disable ML model

**Risk 4: Concept Drift** (model degrades over time)
- **Mitigation**: Continuous monitoring, monthly retraining
- **Fallback**: Alerts trigger model refresh

### Business Risks

**Risk 1: Models Not Used by Team**
- **Mitigation**: Integrate into existing workflows (Gorgias, Slack)
- **Fallback**: Training sessions, documentation

**Risk 2: False Positives Frustrate Customers**
- **Mitigation**: Optimize threshold for business costs
- **Fallback**: Adjust threshold based on feedback

**Risk 3: Budget Overrun**
- **Mitigation**: Fixed-price contractor, milestone payments
- **Fallback**: Pause after Phase 1, evaluate ROI

---

## Recommendation

### Immediate Next Steps

1. **Hire ML Contractor** (Week 1)
   - Post on Upwork/Toptal
   - Budget: $10K-$15K
   - Timeline: 6 weeks

2. **Prepare Data** (Week 1, parallel)
   - Validate combined_sales table
   - Generate training dataset
   - Document data quality

3. **Set Success Criteria** (Week 1)
   - Define minimum AUC (0.85)
   - Define business impact targets
   - Set go/no-go decision points

4. **Phased Rollout** (Weeks 4-8)
   - Week 4: Internal testing (founder only)
   - Week 6: A/B test (50% traffic)
   - Week 8: Full rollout (100% traffic)

### Decision Points

**After Week 3** (Model Training Complete):
- ✅ **GO** if AUC > 0.85 → Deploy to production
- ⚠️ **ITERATE** if AUC 0.75-0.85 → Try ensemble methods
- ❌ **NO-GO** if AUC < 0.75 → Need more data sources

**After Week 6** (A/B Test Results):
- ✅ **GO** if ML model outperforms rules by 20%+ → Full rollout
- ⚠️ **CAUTION** if ML model outperforms by 10-20% → Continue monitoring
- ❌ **ROLLBACK** if ML model underperforms → Investigate

### Expected Outcome

**Best Case** (85% probability):
- Churn AUC: 0.85-0.90
- LTV R²: 0.70-0.75
- Business impact: $70K+/year
- **Timeline**: 8 weeks
- **Cost**: $15K

**Base Case** (80% probability):
- Churn AUC: 0.80-0.85
- LTV R²: 0.65-0.70
- Business impact: $50K+/year
- **Timeline**: 10 weeks
- **Cost**: $20K

**Worst Case** (5% probability):
- Churn AUC: 0.70-0.75 (need more data)
- Pause project, add Klaviyo/GA integration
- **Timeline**: Delayed 3 months
- **Cost**: $10K wasted

---

## Appendix: Code Snippets

### API Integration Example

```python
# Current (rules-based):
@app.get("/api/customers/{customer_id}/churn-risk")
async def get_churn_risk_old(customer_id: str):
    # Rules-based heuristics
    risk_score = 0.0
    if days_since_last > 90:
        risk_score += 0.3
    ...
    return {"risk_score": risk_score}

# New (ML-based):
@app.get("/api/customers/{customer_id}/churn-risk-ml")
async def get_churn_risk_ml(customer_id: str):
    # Extract features
    features = feature_extractor.extract_all_features(...)

    # Predict with ML model
    result = churn_model.predict_with_explanation(features)

    return {
        "churn_probability": 0.73,
        "risk_level": "CRITICAL",
        "top_factors": [
            {"feature": "days_since_last_purchase", "contribution": +0.15},
            {"feature": "frequency_trend_30d", "contribution": +0.12}
        ],
        "recommended_actions": [
            "Send retention email with 15% discount",
            "Flag for account manager outreach"
        ]
    }
```

### Gorgias Integration

```python
# In gorgias_ai_assistant.py

async def _get_customer_analytics(self, customer_id: str) -> Dict:
    """Fetch customer analytics including ML predictions"""

    # Get churn prediction (ML)
    churn_result = await self.analytics_api.get(
        f"/api/customers/{customer_id}/churn-risk-ml"
    )

    # Get LTV prediction (ML)
    ltv_result = await self.analytics_api.get(
        f"/api/customers/{customer_id}/ltv-prediction"
    )

    return {
        "churn": {
            "probability": churn_result["churn_probability"],
            "risk_level": churn_result["risk_level"],
            "top_factors": churn_result["top_factors"]
        },
        "ltv": {
            "historical": ltv_result["ltv_historical"],
            "predicted_12m": ltv_result["ltv_predicted_12m"],
            "total_predicted": ltv_result["ltv_total_predicted"]
        },
        "recommended_actions": churn_result["recommended_actions"]
    }
```

---

**Last Updated**: 2025-11-12
**Status**: Ready for Implementation
**Next Step**: Hire ML contractor, begin Week 1

