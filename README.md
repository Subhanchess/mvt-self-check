# mvt-self-check

`mvt-self-check`, başvuru sayfalarındaki son tarih değişikliklerini izlemek ve farklılık oluştuğunda haberdar olmak için hazırlanmış küçük bir Python yardımcı aracıdır. Komut satırından çalışır ve sonuçları CSV dosyasında saklar.

## Özellikler

- HTML sayfalarından tarihleri CSS seçicisi ya da metin ipucu ile çekme
- Tarih bulunamadığında sayfanın normalize edilmiş özetini (snapshot) karşılaştırma
- Mailgun üzerinden e-posta bildirimi
- Cron veya GitHub Actions gibi zamanlayıcılarla kolay otomasyon

## Gereksinimler

- Python 3.9 veya üzeri
- `requests` ve `beautifulsoup4` bağımlılıkları (``pip install -r requirements.txt`` komutu ile kurulabilir)

## Kurulum

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Yapılandırma

1. `links.csv` dosyasını düzenleyerek izlemek istediğiniz sayfaları ekleyin. Sütunlar:
   - `url`: Kontrol edilecek sayfanın adresi.
   - `selector_or_hint`: Tarihi bulmak için CSS seçici veya metin ipucu.
   - `last_seen`: Son görülen değer. İlk kullanımda boş bırakabilirsiniz.
2. (İsteğe bağlı) Mail bildirimleri için aşağıdaki ortam değişkenlerini ayarlayın:

```bash
export MAILGUN_DOMAIN="<domain>"
export MAILGUN_KEY="<api-anahtarı>"
export EMAIL_TO="alici@example.com"
```

## Çalıştırma

```bash
python check.py
```

Komut, `links.csv` dosyasındaki her URL'yi isteyip seçilen veriyi çözer, değişiklik olduğunda `notify` fonksiyonu ile uyarı yollar ve güncel değeri tekrar CSV dosyasına yazar.

## İzleme kipleri

Betik varsayılan olarak sayfada tarih arar ve `last_seen` sütununa bulduğu değeri kaydeder. Tarih aramak için:

- CSS seçici (`.deadline`, `#application-date` vb.)
- Serbest metin ipucu (`deadline`, `son başvuru`, `application closes` vb.)

Tarih bulunursa aynı değer bir sonraki taramada karşılaştırılır. Tarih bulunamazsa (ör. sayfa sadece liste veya duyuru içeriyorsa) `last_seen` varsayılan olarak boş kalır.

### Snapshot modu

Sayfadaki herhangi bir metin değişikliğini izlemek isterseniz snapshot modunu kullanın. Bunun için `selector_or_hint` değerini aşağıdaki biçimlerden biri ile ayarlayın:

- `snapshot` &mdash; Tüm sayfanın düz metin çıktısını normalize edip SHA-256 özeti ile saklar.
- `snapshot:CSS_SEÇİCİ` &mdash; Yalnızca verilen CSS seçicideki metnin özetini saklar.

Snapshot kipinde betik önce tarih aramayı dener. Tarih bulunamazsa seçilen içeriğin (veya tüm sayfanın) normalize edilmiş düz metnini çıkarır, SHA-256 özeti üretir ve `last_seen` alanına `snapshot:sha256:<özet>` formatında yazar. Metin değiştiğinde yeni bir özet oluşur ve `notify` çalışarak sizi uyarır.

Date-only davranışına geri dönmek için `selector_or_hint` değerinden `snapshot` önekini kaldırmanız yeterlidir.

## Otomasyon

Aracı düzenli aralıklarla çalıştırmak için işletim sistemi zamanlayıcılarını kullanabilirsiniz. Örneğin bir cron girdisi:

```
0 * * * * cd /path/to/mvt-self-check && /usr/bin/python check.py >> /var/log/mvt-self-check.log 2>&1
```

Depoda ayrıca GitHub Actions iş akışı örneği yer alır; uzak depo üzerinde değişiklikleri izlemek için benzer bir yaklaşım uygulayabilirsiniz.

## Sorun giderme

- Yanıt sürelerini kısaltmak için `requests.get` isteğine 30 saniyelik zaman aşımı uygulanır. Ağ problemi durumunda hata mesajı stderr'e yazılır ve CSV dosyası güncellenmez.
- CSS seçicisi hata döndürürse (örneğin dengesiz köşeli parantez), seçim güvenli şekilde atlanır ve tüm sayfa metni snapshot'a dahil edilir.
- `last_seen` alanı `snapshot:` ile başlıyorsa bunun bir tarih değil, metin özeti olduğunu varsayabilirsiniz.
