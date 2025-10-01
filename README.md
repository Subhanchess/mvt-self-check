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
