"""
Simulador de inferencia en tiempo real para detección de vishing.

Envía observaciones una a una al VishingModelWrapper, mide la latencia
en milisegundos de cada llamada y devuelve un DataFrame con los resultados.
"""
import time
import joblib
import boto3
import pandas as pd
import numpy as np
from io import BytesIO
from urllib.parse import urlparse

try:
    from tqdm import tqdm
    _TQDM_AVAILABLE = True
except ImportError:
    _TQDM_AVAILABLE = False


class RealtimeInferenceSimulator:
    """
    Simula un flujo de inferencia en tiempo real enviando observaciones
    una a una al VishingModelWrapper y registrando la latencia en ms.

    Params
    ------
    wrapper_s3_path  : ruta S3 completa al .pkl del VishingModelWrapper
    data_s3_path     : ruta S3 completa al parquet de las 100K observaciones
    bucket           : nombre del bucket (sin s3://)
    results_s3_prefix: prefijo S3 donde se guardarán los resultados
    """

    def __init__(
        self,
        wrapper_s3_path: str,
        data_s3_path: str,
        bucket: str = 'poc-fraude-vishing',
        results_s3_prefix: str = 'proyecto/data/inference_simulation/results',
    ):
        self.wrapper_s3_path   = wrapper_s3_path
        self.data_s3_path      = data_s3_path
        self.bucket            = bucket
        self.results_s3_prefix = results_s3_prefix
        self.s3                = boto3.client('s3')
        self.wrapper           = None
        self.df_data           = None
        self.df_results        = None

    # ── Carga ────────────────────────────────────────────────────────────────

    def load_model(self):
        """Carga el VishingModelWrapper desde S3."""
        parsed = urlparse(self.wrapper_s3_path)
        bkt    = parsed.netloc if parsed.netloc else self.bucket
        key    = parsed.path.lstrip('/')
        buf    = BytesIO()
        self.s3.download_fileobj(bkt, key, buf)
        buf.seek(0)
        self.wrapper = joblib.load(buf)
        print(f'[Simulador] Modelo cargado  : {self.wrapper}')

    def load_data(self):
        """Carga el dataset de inferencia (parquet) desde S3."""
        parsed = urlparse(self.data_s3_path)
        bkt    = parsed.netloc if parsed.netloc else self.bucket
        key    = parsed.path.lstrip('/')
        buf    = BytesIO()
        self.s3.download_fileobj(bkt, key, buf)
        buf.seek(0)
        self.df_data = pd.read_parquet(buf)
        n  = len(self.df_data)
        nv = int(self.df_data['is_vishing'].sum()) if 'is_vishing' in self.df_data.columns else -1
        pct = f'{nv/n*100:.2f}%' if nv >= 0 else 'desconocido'
        print(f'[Simulador] Data cargada    : {n:,} observaciones — vishing {pct}')

    # ── Simulación ────────────────────────────────────────────────────────────

    def run(self, n_max: int = None, show_progress: bool = True) -> pd.DataFrame:
        """
        Ejecuta la simulación enviando observaciones una a una.

        Params
        ------
        n_max         : límite de observaciones (None = todas)
        show_progress : mostrar barra de progreso tqdm

        Returns
        -------
        pd.DataFrame con columnas:
            obs_index, is_vishing_real, label_pred, prediction,
            score_vishing, score_legitimate, threshold_used, latency_ms
        """
        if self.wrapper is None:
            self.load_model()
        if self.df_data is None:
            self.load_data()

        feat_names = self.wrapper.feature_names
        missing    = set(feat_names) - set(self.df_data.columns)
        if missing:
            raise ValueError(f'Features faltantes en el dataset de inferencia: {sorted(missing)}')

        has_gt    = 'is_vishing' in self.df_data.columns
        keep_cols = feat_names + (['is_vishing'] if has_gt else [])
        df        = self.df_data[[c for c in keep_cols if c in self.df_data.columns]].copy()

        if n_max is not None:
            df = df.head(n_max)

        records  = []
        iterator = df.iterrows()
        if show_progress and _TQDM_AVAILABLE:
            iterator = tqdm(iterator, total=len(df), desc='Inferencia en tiempo real')

        print(f'[Simulador] Iniciando simulación — {len(df):,} observaciones individuales...')
        t_sim_start = time.perf_counter()

        for idx, row in iterator:
            obs_dict = {f: float(row[f]) for f in feat_names}

            t0     = time.perf_counter()
            result = self.wrapper.predict_full(obs_dict)
            t1     = time.perf_counter()

            latency_ms = (t1 - t0) * 1_000

            rec = {
                'obs_index'       : idx,
                'label_pred'      : result['label'],
                'prediction'      : result['prediction'],
                'score_vishing'   : result['probability_vishing'],
                'score_legitimate': result['probability_legitimate'],
                'threshold_used'  : result['threshold_used'],
                'latency_ms'      : round(latency_ms, 4),
            }
            if has_gt:
                rec['is_vishing_real'] = int(row['is_vishing'])
            records.append(rec)

        t_sim_end = time.perf_counter()
        total_s   = t_sim_end - t_sim_start
        print(f'[Simulador] Simulación completada en {total_s:.1f}s  '
              f'({len(records)/total_s:,.0f} obs/s)')

        self.df_results = pd.DataFrame(records)
        return self.df_results

    # ── Guardar ───────────────────────────────────────────────────────────────

    def save_results(self, filename: str = 'simulation_results.csv') -> str:
        """Guarda el DataFrame de resultados en S3 como CSV."""
        if self.df_results is None:
            raise RuntimeError('Ejecuta run() antes de guardar.')
        s3_key = f'{self.results_s3_prefix}/{filename}'
        buf    = BytesIO()
        self.df_results.to_csv(buf, index=False)
        buf.seek(0)
        self.s3.upload_fileobj(buf, self.bucket, s3_key)
        path = f's3://{self.bucket}/{s3_key}'
        print(f'[Simulador] Resultados guardados en: {path}')
        return path

    # ── Métricas ──────────────────────────────────────────────────────────────

    def compute_metrics(self) -> dict:
        """
        Computa métricas de detección (si hay ground truth) y de latencia.

        Returns
        -------
        dict con claves: total_obs, total_vishing, total_legitimate,
            total_alerts, alert_rate_pct, vishing_detected, vishing_missed,
            false_alerts, recall, precision, f1,
            lat_mean_ms, lat_median_ms, lat_p95_ms, lat_p99_ms,
            lat_max_ms, lat_min_ms
        """
        if self.df_results is None:
            raise RuntimeError('Ejecuta run() antes de calcular métricas.')
        df  = self.df_results
        lat = df['latency_ms']

        metrics = {
            'total_obs'    : len(df),
            'total_alerts' : int((df['prediction'] == 1).sum()),
            'alert_rate_pct': round((df['prediction'] == 1).mean() * 100, 4),
            'lat_mean_ms'  : round(lat.mean(), 4),
            'lat_median_ms': round(lat.median(), 4),
            'lat_p95_ms'   : round(lat.quantile(0.95), 4),
            'lat_p99_ms'   : round(lat.quantile(0.99), 4),
            'lat_max_ms'   : round(lat.max(), 4),
            'lat_min_ms'   : round(lat.min(), 4),
        }

        if 'is_vishing_real' in df.columns:
            tp = int(((df['prediction'] == 1) & (df['is_vishing_real'] == 1)).sum())
            fp = int(((df['prediction'] == 1) & (df['is_vishing_real'] == 0)).sum())
            fn = int(((df['prediction'] == 0) & (df['is_vishing_real'] == 1)).sum())
            tn = int(((df['prediction'] == 0) & (df['is_vishing_real'] == 0)).sum())

            recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            f1        = (2 * recall * precision / (recall + precision)
                         if (recall + precision) > 0 else 0.0)

            metrics.update({
                'total_vishing'   : int((df['is_vishing_real'] == 1).sum()),
                'total_legitimate': int((df['is_vishing_real'] == 0).sum()),
                'vishing_detected': tp,
                'vishing_missed'  : fn,
                'false_alerts'    : fp,
                'true_negatives'  : tn,
                'recall'          : round(recall, 4),
                'precision'       : round(precision, 4),
                'f1'              : round(f1, 4),
            })

        return metrics
