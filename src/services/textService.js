import { promises as fs } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const dataDir = path.resolve(__dirname, '../../data');

const formatContent = (name, fileName, content) => ({
  name,
  fileName,
  lines: content.split(/\r?\n/),
  content,
});

export async function getAllTextResources() {
  const entries = await fs.readdir(dataDir, { withFileTypes: true });
  const textFiles = entries.filter((entry) => entry.isFile() && path.extname(entry.name) === '.txt');

  const resources = await Promise.all(
    textFiles.map(async (entry) => {
      const filePath = path.join(dataDir, entry.name);
      const content = await fs.readFile(filePath, 'utf-8');
      const name = path.basename(entry.name, '.txt');
      return formatContent(name, entry.name, content);
    }),
  );

  return resources;
}

export async function getTextResource(name) {
  const fileName = `${name}.txt`;
  const filePath = path.join(dataDir, fileName);

  try {
    const content = await fs.readFile(filePath, 'utf-8');
    return formatContent(name, fileName, content);
  } catch (error) {
    if (error.code === 'ENOENT') {
      return null;
    }
    throw error;
  }
}
