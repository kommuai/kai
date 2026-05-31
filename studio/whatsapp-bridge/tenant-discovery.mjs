/**
 * Discover tenant workspaces that should run a persistent Baileys worker socket.
 */
import fs from "fs";
import path from "path";
import yaml from "js-yaml";

function tenantsRoot() {
  const env = process.env.SHADOU_TENANTS_ROOT;
  if (env) return path.resolve(env);
  return path.resolve(process.env.HOME || "/tmp", "workspace");
}

function credsLookLinked(credsPath) {
  try {
    const raw = fs.readFileSync(credsPath, "utf8");
    const creds = JSON.parse(raw);
    const me = creds?.me;
    if (me && (me.id || me.name)) return true;
    return Boolean(creds?.registered);
  } catch {
    return false;
  }
}

/**
 * @returns {Array<{ key: string, slug: string, home: string, authDir: string, phone?: string }>}
 */
export function discoverWhatsAppTenants() {
  const root = tenantsRoot();
  if (!fs.existsSync(root)) return [];

  const out = [];
  for (const name of fs.readdirSync(root)) {
    if (!name.startsWith("shadou-tenant-")) continue;
    const home = path.join(root, name);
    if (!fs.statSync(home).isDirectory()) continue;

    const wsPath = path.join(home, "workspace.yaml");
    if (!fs.existsSync(wsPath)) continue;

    let ws;
    try {
      ws = yaml.load(fs.readFileSync(wsPath, "utf8")) || {};
    } catch {
      continue;
    }

    const channels = ws.channels && typeof ws.channels === "object" ? ws.channels : {};
    const inbound = channels.inbound && typeof channels.inbound === "object" ? channels.inbound : {};
    const provider = String(inbound.provider || "none").toLowerCase();
    const baileys = channels.whatsapp_baileys && typeof channels.whatsapp_baileys === "object"
      ? channels.whatsapp_baileys
      : {};

    if (provider !== "whatsapp_baileys" || !baileys.enabled) continue;

    const authRel = String(baileys.auth_dir || "data/whatsapp/baileys-auth").replace(/^\//, "");
    const authDir = path.resolve(home, authRel);
    const credsPath = path.join(authDir, "creds.json");
    if (!fs.existsSync(credsPath) || !credsLookLinked(credsPath)) continue;

    const slug = name.replace(/^shadou-tenant-/, "");
    out.push({
      key: home,
      slug,
      home,
      authDir,
      phone: baileys.phone ? String(baileys.phone) : undefined,
    });
  }

  out.sort((a, b) => a.slug.localeCompare(b.slug));
  return out;
}

export { tenantsRoot };
