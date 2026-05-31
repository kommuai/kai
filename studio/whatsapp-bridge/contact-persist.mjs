/**
 * Persist WhatsApp handle / phone into tenant memory_facts + contact-directory.json.
 */
import { spawn } from "child_process";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function shadouRepoRoot() {
  if (process.env.SHADOU_REPO) return path.resolve(process.env.SHADOU_REPO);
  return path.resolve(__dirname, "../..");
}

function pythonBin() {
  return process.env.SHADOU_PYTHON || "python3";
}

function storeScript() {
  return path.join(shadouRepoRoot(), "studio", "backend", "store_contact_meta.py");
}

function updateContactDirectory(home, userId, meta) {
  const dirPath = path.join(home, "data", "whatsapp");
  const filePath = path.join(dirPath, "contact-directory.json");
  try {
    fs.mkdirSync(dirPath, { recursive: true });
    let data = {};
    try {
      data = JSON.parse(fs.readFileSync(filePath, "utf8"));
    } catch {
      /* new file */
    }
    const prev = data[userId] || {};
    const next = {
      pushName: (meta.pushName || prev.pushName || "").trim(),
      phone: (meta.phone || prev.phone || "").trim(),
      updatedAt: new Date().toISOString(),
    };
    if (!next.pushName && !next.phone) return;
    data[userId] = next;
    fs.writeFileSync(filePath, JSON.stringify(data, null, 2));
  } catch {
    /* non-fatal */
  }
}

/**
 * @param {string} home tenant workspace (SHADOU_HOME)
 * @param {string} userId session user id
 * @param {{ pushName?: string, phone?: string, notify?: string, verifiedName?: string }} meta
 */
export function persistContactMeta(home, userId, meta) {
  const push = (meta.pushName || meta.notify || "").trim();
  const phone = (meta.phone || "").trim();
  const verified = (meta.verifiedName || "").trim();
  if (!push && !phone && !verified) return;

  updateContactDirectory(home, userId, { pushName: push, phone });

  const payload = JSON.stringify({
    pushName: push,
    phone,
    verifiedName: verified,
  });

  const proc = spawn(pythonBin(), [storeScript(), home, userId, payload], {
    env: {
      ...process.env,
      SHADOU_HOME: home,
      PYTHONPATH: [shadouRepoRoot(), process.env.PYTHONPATH].filter(Boolean).join(path.delimiter),
    },
    cwd: shadouRepoRoot(),
    stdio: "ignore",
  });
  proc.unref();
}
