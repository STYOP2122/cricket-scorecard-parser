# Cricket Scorecard Parser

Приложение для извлечения статистики игроков со страницы матча ESPNcricinfo. Сервер открывает страницу через Puppeteer, считывает таблицы и возвращает данные в JSON. В репозитории также есть веб-интерфейс для работы с парсером.

## Данные

- Названия двух команд.
- Статистика бэттеров: runs, fours и sixes.
- Статистика боулеров: wickets и runs.

## Технологии

Node.js, Express, Puppeteer и браузерный JavaScript.

## Запуск

Понадобятся Node.js, npm и доступ в интернет. При установке зависимостей загружается браузер для Puppeteer.

```bash
git clone https://github.com/STYOP2122/cricket-scorecard-parser.git
cd cricket-scorecard-parser
npm install
node server.js
```

Откройте `http://localhost:3000/index.html` и укажите адрес страницы со статистикой матча ESPNcricinfo.

## API

`GET /api/scrape?url=<URL страницы матча>` возвращает `teams`, `team1Batters`, `team2Batters`, `team1Bowlers` и `team2Bowlers`. Значение параметра `url` нужно URL-кодировать.

Парсер рассчитан на страницу с четырьмя таблицами статистики. Изменения разметки ESPNcricinfo или неполные данные матча могут потребовать изменения селекторов в `server.js`.

## Файлы

- `server.js` — сервер и извлечение таблиц.
- `public/index.html` — веб-интерфейс.
