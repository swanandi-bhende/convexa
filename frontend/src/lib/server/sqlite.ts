import { readFile } from "node:fs/promises";
import path from "node:path";

import initSqlJs, { type Database, type QueryExecResult } from "sql.js";

const SQLITE_PREFIX = "sqlite:///";
const DEFAULT_SQLITE_PATH = path.resolve(process.cwd(), "../utils/db/debate.db");

let sqlModulePromise: Promise<Awaited<ReturnType<typeof initSqlJs>>> | null = null;

function resolveDatabasePath() {
  const databaseUrl = process.env.DATABASE_URL || SQLITE_PREFIX + "../utils/db/debate.db";

  if (!databaseUrl.startsWith(SQLITE_PREFIX)) {
    return DEFAULT_SQLITE_PATH;
  }

  const rawPath = databaseUrl.slice(SQLITE_PREFIX.length);
  return path.isAbsolute(rawPath) ? rawPath : path.resolve(process.cwd(), rawPath);
}

async function loadSqlModule() {
  if (!sqlModulePromise) {
    sqlModulePromise = initSqlJs({
      locateFile: (file: string) => path.join(process.cwd(), "node_modules/sql.js/dist", file),
    });
  }

  return sqlModulePromise;
}

export async function openSqliteDatabase(): Promise<Database | null> {
  const databasePath = resolveDatabasePath();

  try {
    const databaseBytes = await readFile(databasePath);
    const sqlModule = await loadSqlModule();
    return new sqlModule.Database(new Uint8Array(databaseBytes));
  } catch {
    return null;
  }
}

export async function querySqlite<T extends Record<string, unknown>>(
  statement: string,
  params: Array<string | number | bigint | null> = []
): Promise<T[]> {
  const database = await openSqliteDatabase();
  if (!database) {
    return [];
  }

  try {
    const prepared = database.prepare(statement);
    if (params.length) {
      prepared.bind(params as never);
    }

    const rows: T[] = [];
    while (prepared.step()) {
      rows.push(prepared.getAsObject() as T);
    }

    prepared.free();
    return rows;
  } finally {
    database.close();
  }
}

export function rowsToObjects(results: QueryExecResult[]): Record<string, unknown>[] {
  const rows: Record<string, unknown>[] = [];

  for (const result of results) {
    const columns = result.columns;
    for (const row of result.values) {
      const entry: Record<string, unknown> = {};
        columns.forEach((column: string, index: number) => {
        entry[column] = row[index];
      });
      rows.push(entry);
    }
  }

  return rows;
}

export function databasePath() {
  return resolveDatabasePath();
}
