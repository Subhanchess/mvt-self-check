# mvt-self-check

## Metin tabanlı durum takibi

Tarih bulunmayan sayfalarda başvuru durumlarını izlemek için `links.csv` dosyasındaki
`selector_or_hint` sütununa aramak istediğiniz durum ifadelerini yazabilirsiniz.
Aşağıdaki anahtar sözcükler desteklenir:

- `application open`
- `applications open`
- `application closed`
- `applications closed`
- `başvuru açık`
- `başvurular açık`
- `başvuru kapandı`
- `başvurular kapandı`

Bot bu ifadelerden birini bulduğunda `last_seen` alanına ilgili metni yazar ve önceki
kayıttan farklıysa bildirim gönderir.

## Web arayüzü

Takip edilen bağlantıları CSV dosyasına elle yazmak yerine küçük bir Flask arayüzü
sağlanmıştır. Çalıştırmak için:

```bash
python -m pip install -r requirements.txt
flask --app app run
```

Arayüz `http://127.0.0.1:5000/` adresinde açılır. Buradan:

- Yeni bağlantı ekleyebilir, isteğe bağlı olarak CSS seçicisi veya anahtar kelime ipucu
  yazabilirsiniz.
- Mevcut kayıtları silebilirsiniz.
- "Manuel Tarama Çalıştır" düğmesi ile `check.py`deki aynı taramayı tetikleyebilirsiniz;
  değişiklik bulunursa `MAILGUN_*` ve `EMAIL_TO` ortam değişkenleri kullanılarak e-posta
  gönderilir.

İlk tarama sırasında `links.csv` dosyası otomatik oluşturulur. Üretim ortamında Flask
uygulamasını bir WSGI sunucusu üzerinden çalıştırabilir veya sadece hızlı yerel kullanım
için değerlendirebilirsiniz.
