#!/usr/bin/env python3
"""S3 bucket'taki resimleri (veya tüm dosyaları) yerel klasöre indirir.

SALT OKUNUR: Yalnızca ListObjectsV2 ve GetObject çağrıları yapılır.
S3 üzerinde silme/yükleme/değiştirme işlemi yapılmaz.

Kullanım:
    .env dosyasına S3_ENDPOINT, S3_ACCESS_KEY, S3_SECRET_KEY, S3_BUCKET (ops. S3_REGION) yaz.
    python s3_download.py                 # sadece resimler
    python s3_download.py --all           # tüm dosyalar
    python s3_download.py --prefix foto/ --out ./indirilenler
"""
import argparse
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv

# Betiğin yanındaki .env dosyasını okur (çalışma dizininden bağımsız)
load_dotenv(Path(__file__).resolve().parent / ".env")

IMAGE_EXTS = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tif", ".tiff",
    ".svg", ".ico", ".heic", ".heif", ".avif",
}


def parse_args():
    p = argparse.ArgumentParser(description="S3'ten salt okunur indirme")
    p.add_argument("--endpoint", default=os.getenv("S3_ENDPOINT"), help="S3 endpoint URL (AWS için boş bırak)")
    p.add_argument("--access-key", default=os.getenv("S3_ACCESS_KEY"))
    p.add_argument("--secret-key", default=os.getenv("S3_SECRET_KEY"))
    p.add_argument("--bucket", default=os.getenv("S3_BUCKET"))
    p.add_argument("--region", default=os.getenv("S3_REGION"))
    p.add_argument("--prefix", default="", help="Sadece bu önekle başlayan anahtarlar")
    p.add_argument("--out", default="./downloads", help="İndirme klasörü")
    p.add_argument("--all", action="store_true", help="Sadece resimler yerine tüm dosyalar")
    p.add_argument("--workers", type=int, default=8, help="Paralel indirme sayısı")
    p.add_argument("--dry-run", action="store_true", help="Sadece listele, indirme")
    return p.parse_args()


def make_client(a):
    endpoint = (a.endpoint or "").strip().rstrip("/")
    if endpoint and "://" not in endpoint:
        endpoint = "https://" + endpoint  # şema yazılmadıysa https varsay
    return boto3.client(
        "s3",
        endpoint_url=endpoint or None,
        aws_access_key_id=a.access_key,
        aws_secret_access_key=a.secret_key,
        region_name=a.region or None,
        config=Config(
            retries={"max_attempts": 5, "mode": "standard"},
            connect_timeout=15,  # bağlantı takılırsa sonsuza kadar bekleme
            read_timeout=60,
        ),
    )


def list_keys(s3, bucket, prefix, only_images):
    """(key, size) üretir. Yalnızca list_objects_v2 kullanır."""
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith("/"):  # klasör işaretçisi
                continue
            if only_images and Path(key).suffix.lower() not in IMAGE_EXTS:
                continue
            yield key, obj["Size"]


def safe_target(out_dir: Path, key: str) -> Path:
    """Anahtarı out_dir içinde tutar (../ ile dışarı çıkmayı engeller)."""
    target = (out_dir / key).resolve()
    if out_dir.resolve() not in target.parents:
        raise ValueError(f"Güvensiz anahtar atlandı: {key}")
    return target


def download_one(s3, bucket, key, size, out_dir: Path):
    target = safe_target(out_dir, key)
    if target.exists() and target.stat().st_size == size:
        return key, "atlandı (zaten var)"
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".part")
    s3.download_file(bucket, key, str(tmp))  # GetObject
    tmp.replace(target)
    return key, "indirildi"


def main():
    a = parse_args()
    missing = [n for n, v in (("access-key", a.access_key), ("secret-key", a.secret_key), ("bucket", a.bucket)) if not v]
    if missing:
        sys.exit(f"Eksik bilgi: {', '.join(missing)} (argüman veya S3_* ortam değişkeni ile ver)")

    s3 = make_client(a)
    out_dir = Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        items = list(list_keys(s3, a.bucket, a.prefix, only_images=not a.all))
    except (ClientError, BotoCoreError) as e:
        hint = ""
        if isinstance(e, ClientError) and e.response["Error"].get("Code") == "AccessDenied":
            hint = (
                "\nİpucu: anahtar çifti, bucket adı ve endpoint'i kontrol et; "
                "anahtarın bu bucket için ListBucket/GetObject izni olmalı."
            )
        sys.exit(f"Listeleme hatası: {e}{hint}")

    total = sum(s for _, s in items)
    print(f"{len(items)} dosya bulundu ({total / 1024 / 1024:.1f} MB)")
    if a.dry_run:
        for k, s in items:
            print(f"  {k} ({s} B)")
        return

    ok = fail = 0
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futures = {ex.submit(download_one, s3, a.bucket, k, s, out_dir): k for k, s in items}
        for i, f in enumerate(as_completed(futures), 1):
            key = futures[f]
            try:
                _, status = f.result()
                ok += 1
                print(f"[{i}/{len(items)}] {key}: {status}")
            except Exception as e:  # tek dosya hatası diğerlerini durdurmasın
                fail += 1
                print(f"[{i}/{len(items)}] {key}: HATA {e}", file=sys.stderr)

    print(f"Bitti. Başarılı: {ok}, hatalı: {fail}, klasör: {out_dir.resolve()}")


if __name__ == "__main__":
    main()
