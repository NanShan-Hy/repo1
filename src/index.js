import express from 'express';
import morgan from 'morgan';
import path from 'path';
import { fileURLToPath } from 'url';

import apiRouter from './routes/api.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 3000;
const publicDir = path.resolve(__dirname, '../public');

app.use(morgan('dev'));
app.use(express.json());

app.use('/api', apiRouter);
app.use(express.static(publicDir));

app.use((req, res, next) => {
  if (req.method.toUpperCase() === 'GET' && !req.path.startsWith('/api/')) {
    res.sendFile(path.join(publicDir, 'index.html'));
    return;
  }
  next();
});

app.use((err, req, res, next) => {
  console.error('[ERROR]', err);
  res.status(err.status || 500).json({
    message: err.message || '服务器内部错误',
  });
});

app.listen(PORT, () => {
  console.log(`🚀 Web 服务已启动，访问 http://localhost:${PORT}`);
});
