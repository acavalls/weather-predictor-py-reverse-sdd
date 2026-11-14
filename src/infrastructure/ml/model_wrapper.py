"""Custom model wrapper used during training — must be importable at prediction time.

This class is pickled inside model.pkl. It MUST remain importable from this
module path for joblib.load() to deserialize the model correctly.
"""

from __future__ import annotations

import numpy as np


class MultiOutputRegressorWithProgress:
    """Wrapper that mimics sklearn MultiOutputRegressor API with tqdm progress.

    Stores multiple trained estimators (one per target variable) and provides
    a unified predict() method that stacks their outputs.
    """

    def __init__(self, estimators):
        self.estimators_ = estimators

    def predict(self, X):
        return np.column_stack([e.predict(X) for e in self.estimators_])

    def score(self, X, y):
        from sklearn.metrics import r2_score

        y_pred = self.predict(X)
        return r2_score(y, y_pred, multioutput="uniform_average")
