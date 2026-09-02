// 빌드 시점에 public/data 를 읽어 정적 경로를 만든다 (output: export).
import fs from "node:fs";
import path from "node:path";

const DATA = path.join(process.cwd(), "public", "data");

export function readData(rel) {
  try {
    return JSON.parse(fs.readFileSync(path.join(DATA, rel), "utf-8"));
  } catch {
    return null;
  }
}

export function listData(dir) {
  try {
    return fs.readdirSync(path.join(DATA, dir))
      .filter((f) => f.endsWith(".json"))
      .map((f) => f.slice(0, -5));
  } catch {
    return [];
  }
}
