import { promises as fs } from 'fs';
import path from 'path';

export async function getTeams() {
  const teamsPath = path.join(process.cwd(), 'macroservice', 'config', 'teams.json');
  const data = await fs.readFile(teamsPath, 'utf8');
  return JSON.parse(data);
}
