import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import uploadRoutes from './routes/upload.js';
import summaryRoutes from './routes/summary.js';
import emailRoutes from './routes/email.js';
import summariesRoutes from './routes/summaries.js';
import exportRoutes from './routes/export.js';
import { authenticateJwt } from './middleware/auth.js';

dotenv.config();

const app = express();
const port = process.env.PORT || 5000;

const allowedOrigins = (process.env.CORS_ORIGINS || 'http://localhost:3000,http://localhost:5173')
  .split(',')
  .map((v) => v.trim())
  .filter(Boolean)
  .filter((origin) => origin !== '*');

const allowedOriginSet = new Set(allowedOrigins);

app.use(cors({
  origin(origin, callback) {
    if (!origin) return callback(null, true);
    const allowed = allowedOriginSet.has(origin);
    callback(allowed ? null : new Error('Not allowed by CORS'), allowed);
  },
  credentials: true,
}));
app.use(express.json());

app.set('trust proxy', true);

app.use('/api/upload', uploadRoutes);
app.use('/api/summary', authenticateJwt, summaryRoutes);
app.use('/api/email', emailRoutes);
app.use('/api/summaries', authenticateJwt, summariesRoutes);
app.use('/api/export', exportRoutes);

app.get('/', (req, res) => {
  res.json({ message: 'Meeting Notes API is running' });
});

app.listen(port, () => {
  console.log(`Server running on port ${port}`);
});
