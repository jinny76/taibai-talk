module.exports = {
  apps: [{
    name: 'taibai',
    script: 'G:/projects/DBInputSync/main.py',
    interpreter: 'G:/projects/DBInputSync/.venv/Scripts/python.exe',
    args: '-p 57777 --url https://ime.kingfisher.live --password kingfisher123',
    cwd: 'G:/projects/DBInputSync',
    watch: false,
    autorestart: true,
    max_restarts: 10,
    restart_delay: 1000,
    env: {
      PYTHONUNBUFFERED: '1'
    }
  }]
};
