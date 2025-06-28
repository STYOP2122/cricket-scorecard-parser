const express = require('express');
const puppeteer = require('puppeteer');
const cors = require('cors');
const path = require('path');

const app = express();
app.use(cors());
app.use(express.static(path.join(__dirname, 'public')));

// API endpoint
app.get('/api/scrape', async (req, res) => {
    try {
        const { url } = req.query;
        if (!url) {
            return res.status(400).json({ error: 'URL parameter is required' });
        }

        console.log('Requesting URL:', url);
        const data = await scrapeESPN(url);
        res.json(data);
    } catch (err) {
        console.error('Scraping error:', err);
        res.status(500).json({ error: err.message });
    }
});

async function scrapeESPN(url) {
    const browser = await puppeteer.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    const page = await browser.newPage();
    await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.64 Safari/537.36');

    console.log('Navigating to URL:', url);
    await page.goto(url, {
        waitUntil: 'networkidle2',
        timeout: 60000
    });

    await page.waitForSelector('.ds-w-full.ds-table', { timeout: 30000 });

    const data = await page.evaluate(() => {
        const parsePlayers = (table, team, isBowler = false) => {
            const players = [];
            const rows = table.querySelectorAll('tbody tr');

            rows.forEach(row => {
                // Пропускаем скрытые строки с деталями викетов
                if (row.classList.contains('ds-hidden')) return;

                const cells = row.querySelectorAll('td');
                if (cells.length < 4) return;

                const playerName = cells[0]?.textContent?.trim();
                if (!playerName || playerName.includes('Extras') || playerName.includes('Total') || playerName.includes('Did not bat')) return;

                const player = {
                    player: playerName,
                    team: team
                };

                if (!isBowler) {
                    player.runs = cells[2]?.textContent?.trim();
                    player.fours = cells[5]?.textContent?.trim();
                    player.sixes = cells[6]?.textContent?.trim();
                } else {
                    // Корректное извлечение викетов
                    const wicketsCell = cells[4];
                    let wickets = '0';

                    if (wicketsCell) {
                        const span = wicketsCell.querySelector('span');
                        if (span) {
                            const strong = span.querySelector('strong');
                            if (strong) wickets = strong.textContent.trim();
                        } else {
                            const strong = wicketsCell.querySelector('strong');
                            wickets = strong ? strong.textContent.trim() : wicketsCell.textContent.trim();
                        }
                    }

                    player.wickets = wickets.replace(/\D/g, '') || '0';
                    player.runs = cells[3]?.textContent?.trim();
                }

                players.push(player);
            });

            return players;
        };

        const tables = document.querySelectorAll('.ds-w-full.ds-table');
        if (tables.length < 4) return { error: 'Not enough data tables found' };

        const teamHeaders = document.querySelectorAll('.ds-text-title-xs.ds-font-bold.ds-capitalize');
        const team1 = teamHeaders[0]?.textContent?.trim() || 'Team 1';
        const team2 = teamHeaders[1]?.textContent?.trim() || 'Team 2';

        // Правильное распределение таблиц
        const team1Batters = parsePlayers(tables[0], team1);
        const team2Bowlers = parsePlayers(tables[1], team2, true); // <-- этот был неправильно как team1
        const team2Batters = parsePlayers(tables[2], team2);
        const team1Bowlers = parsePlayers(tables[3], team1, true); // <-- этот был неправильно как team2


        return {
            teams: { team1, team2 },
            team1Batters,
            team2Batters,
            team1Bowlers,
            team2Bowlers
        };
    });

    await browser.close();
    return data;
}

const PORT = 3000;
app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`);
    console.log(`Open in browser: http://localhost:${PORT}/index.html`);
});
