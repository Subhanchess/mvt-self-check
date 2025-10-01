# mvt-self-check

Bu proje, belirtilen bağlantılardaki son başvuru tarihlerini izleyip değişiklik olduğunda e-posta ile bildiren basit bir denetleyicidir.

## Kullanım

1. `links.csv` dosyasına izleyeceğiniz URL'leri ekleyin. Dosya şu sütunları içerir:
   - `url`: Kontrol edilecek sayfanın adresi.
   - `selector_or_hint`: Tarihi bulmak için CSS seçici ya da serbest metin ipucu.
   - `last_seen`: Son görülen değer; ilk kez boş bırakabilirsiniz.
2. `python check.py` komutu ile kontrolü çalıştırın. Mailgun bilgilerini ortam değişkenleri ile ayarlarsanız, değişiklikler e-posta ile bildirilir.

## İzleme kipleri

Varsayılan olarak betik, sayfa içeriğinde tarih arar ve `last_seen` sütununda bu tarih saklanır. Şu ipuçları date-only izlemede kullanılır:

- CSS seçici (`.deadline`, `#application-date` vb.)
- Serbest metin ipuçları (`deadline`, `son başvuru` vb.)

Tarih bulunamazsa boş değer döner ve daha önceki sonuçla aynı kalır.

Sayfadaki herhangi bir metin değişikliğini izlemek isterseniz "anlık görüntü" kipini (snapshot mode) kullanabilirsiniz. Bunun için `selector_or_hint` değerini aşağıdaki biçimlerden biriyle ayarlayın:

- `snapshot` &mdash; Tüm sayfa metninin normalize edilmiş özetini (SHA-256) saklar.
- `snapshot:CSS_SEÇİCİ` &mdash; Sadece verilen CSS seçicideki metnin özetini saklar.

Snapshot kipinde betik yine önce tarih aramayı dener; tarih bulunamazsa seçilen içeriğin düz metnini normalize edip SHA-256 özetiyle `last_seen` sütununda saklar. Metin değiştiğinde yeni özet üretildiği için `notify` çağrılır ve değişiklikten haberdar olursunuz.

Date-only davranışına geri dönmek için `selector_or_hint` değerinden `snapshot` önekini kaldırmanız yeterlidir.
