# S3 Downloader

S3 uyumlu bir depolama sunucusundaki (AWS S3, MinIO, Wasabi, DigitalOcean Spaces vb.) resimleri veya tüm dosyaları yerel klasöre indiren basit bir Python betiği.

## Salt okunur

Betik S3'e yalnızca iki tür istek gönderir:

- `ListObjectsV2` (dosyaları listeleme)
- `GetObject` (dosyayı indirme)

Silme, yükleme veya değiştirme çağrısı kodda yoktur. Ek güvence için S3 tarafında bu anahtara yalnızca `s3:ListBucket` ve `s3:GetObject` izinlerini veren bir kullanıcı tanımlamanı öneririm.

## Kurulum

```bash
pip install -r requirements.txt
cp .env.example .env
```

Ardından `.env` dosyasını doldur:

```env
S3_ENDPOINT=https://s3.ornek.com
S3_ACCESS_KEY=...
S3_SECRET_KEY=...
S3_BUCKET=bucket-adi
S3_REGION=
```

| Değişken | Zorunlu | Açıklama |
|---|---|---|
| `S3_ENDPOINT` | Hayır | S3 sunucu adresi. AWS S3 için boş bırak. |
| `S3_ACCESS_KEY` | Evet | Erişim anahtarı |
| `S3_SECRET_KEY` | Evet | Gizli anahtar |
| `S3_BUCKET` | Evet | Bucket adı |
| `S3_REGION` | Hayır | Bölge (ör. `eu-central-1`) |

`.env` dosyası `.gitignore` içindedir, commit'lenmez.

## Kullanım

```bash
python s3_download.py --dry-run                  # önce sadece listele
python s3_download.py                            # sadece resimleri indir
python s3_download.py --all                      # tüm dosyaları indir
python s3_download.py --prefix foto/ --out ./indirilenler
```

### Seçenekler

| Seçenek | Varsayılan | Açıklama |
|---|---|---|
| `--prefix` | boş | Sadece bu önekle başlayan anahtarları al |
| `--out` | `./downloads` | İndirme klasörü |
| `--all` | kapalı | Sadece resimler yerine tüm dosyaları indir |
| `--workers` | `8` | Paralel indirme sayısı |
| `--dry-run` | kapalı | Sadece listele, indirme |
| `--endpoint`, `--access-key`, `--secret-key`, `--bucket`, `--region` | `.env` | `.env` değerlerini geçersiz kılar |

## Davranış

- **Resim filtresi:** jpg, jpeg, png, gif, webp, bmp, tif, tiff, svg, ico, heic, heif, avif. Diğer dosyalar için `--all` kullan.
- **Klasör yapısı:** Bucket'taki klasör yapısı yerelde korunur.
- **Devam etme:** Aynı boyutta dosya zaten varsa atlanır. Yarım kalırsa betiği yeniden çalıştırabilirsin.
- **Yarım dosyalar:** İndirme sırasında `.part` uzantılı geçici dosya kullanılır, bittiğinde asıl adına çevrilir.
- **Hata yönetimi:** Bir dosya hata verirse diğerleri devam eder, sonda başarılı ve hatalı sayıları yazdırılır.
- **Güvenlik:** `../` içeren anahtarlar indirme klasörünün dışına yazamaz, bu anahtarlar atlanır.

## Dosyalar

```
s3_download.py    ana betik
requirements.txt  bağımlılıklar (boto3, python-dotenv)
.env.example      örnek ayar dosyası
.gitignore        .env ve downloads/ hariç tutulur
```
