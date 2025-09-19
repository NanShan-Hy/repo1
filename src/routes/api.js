import { Router } from 'express';

import { getAllTextResources, getTextResource } from '../services/textService.js';

const router = Router();

router.get('/health', (req, res) => {
  res.json({ status: 'ok' });
});

router.get('/texts', async (req, res, next) => {
  try {
    const list = await getAllTextResources();
    res.json(list);
  } catch (error) {
    next(error);
  }
});

router.get('/texts/:name', async (req, res, next) => {
  try {
    const resource = await getTextResource(req.params.name);
    if (!resource) {
      res.status(404).json({ message: '未找到指定的文本资源' });
      return;
    }
    res.json(resource);
  } catch (error) {
    next(error);
  }
});

export default router;
