/**
 * PP5 WhatsApp Chatbot — Baileys WhatsApp Client
 *
 * Connects to WhatsApp via the Baileys library using a spare phone number.
 * - On first run: displays a QR code in the terminal for scanning.
 * - On subsequent runs: reconnects automatically using saved auth state.
 * - Forwards incoming messages to the FastAPI backend.
 * - Exposes a POST /send endpoint for the backend to send replies.
 */

const {
  default: makeWASocket,
  DisconnectReason,
  useMultiFileAuthState,
  fetchLatestBaileysVersion,
} = require("@whiskeysockets/baileys");
const express = require("express");
const pino = require("pino");
const qrcode = require("qrcode-terminal");
const path = require("path");
const http = require("http");

// ─── Configuration ──────────────────────────────────────────────────────────

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";
const BAILEYS_PORT = parseInt(process.env.BAILEYS_PORT || "3001", 10);
const AUTH_DIR = path.join(__dirname, "auth_info");

// Pino logger (quiet mode for Baileys internals)
const logger = pino({ level: "info" });

// ─── Express Server (for receiving send requests from backend) ──────────────

const app = express();
app.use(express.json());

/** @type {import("@whiskeysockets/baileys").WASocket | null} */
let sock = null;

/**
 * POST /send
 * Body: { "phone": "+919999999999", "message": "Hello!" }
 *
 * Called by the FastAPI backend to send a WhatsApp reply.
 */
app.post("/send", async (req, res) => {
  try {
    const { phone, message } = req.body;

    if (!phone || !message) {
      return res.status(400).json({ error: "phone and message are required" });
    }

    if (!sock) {
      return res.status(503).json({ error: "WhatsApp not connected" });
    }

    // Format phone for WhatsApp JID
    let jid = phone.replace(/\+/g, "").replace(/\s/g, "");
    if (!jid.includes("@")) {
      jid = jid + "@s.whatsapp.net";
    }

    await sock.sendMessage(jid, { text: message });
    logger.info({ phone, messagePreview: message.substring(0, 60) }, "Message sent");

    return res.json({ status: "sent", phone });
  } catch (err) {
    logger.error({ err }, "Failed to send message");
    return res.status(500).json({ error: err.message });
  }
});

/**
 * GET /health
 * Quick health check — returns connection status.
 */
app.get("/health", (req, res) => {
  res.json({
    status: sock ? "connected" : "disconnected",
    service: "pp5-baileys-whatsapp",
  });
});

// ─── Forward incoming messages to FastAPI backend ───────────────────────────

/**
 * Send an incoming WhatsApp message to the FastAPI backend for processing.
 */
async function forwardToBackend(phone, message, pushName) {
  const payload = JSON.stringify({
    phone,
    message,
    profile_name: pushName || "",
  });

  const url = new URL("/webhook/baileys", BACKEND_URL);

  return new Promise((resolve, reject) => {
    const req = http.request(
      url,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Content-Length": Buffer.byteLength(payload),
        },
        timeout: 30000,
      },
      (res) => {
        let data = "";
        res.on("data", (chunk) => (data += chunk));
        res.on("end", () => {
          logger.info(
            { status: res.statusCode, phone },
            "Backend response received"
          );
          resolve(data);
        });
      }
    );

    req.on("error", (err) => {
      logger.error({ err, phone }, "Failed to forward to backend");
      reject(err);
    });

    req.write(payload);
    req.end();
  });
}

// ─── Baileys WhatsApp Connection ────────────────────────────────────────────

async function startWhatsApp() {
  // Load or create auth state
  const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);
  const { version } = await fetchLatestBaileysVersion();

  logger.info({ version }, "Starting Baileys WhatsApp connection");

  sock = makeWASocket({
    version,
    auth: state,
    logger: pino({ level: "silent" }), // Silence Baileys internal logs
    printQRInTerminal: false, // We'll handle QR ourselves for better display
    browser: ["PP5 Chatbot", "Chrome", "1.0.0"],
    // Reconnect on failure
    connectTimeoutMs: 60000,
    defaultQueryTimeoutMs: 0,
    keepAliveIntervalMs: 25000,
  });

  // ── Connection events ──────────────────────────────────────────────────

  sock.ev.on("connection.update", (update) => {
    const { connection, lastDisconnect, qr } = update;

    // Display QR code in terminal
    if (qr) {
      console.log("\n");
      console.log("═══════════════════════════════════════════════════");
      console.log("  📱 SCAN THIS QR CODE WITH YOUR WHATSAPP");
      console.log("  Open WhatsApp → Settings → Linked Devices → Link a Device");
      console.log("═══════════════════════════════════════════════════");
      console.log("\n");
      qrcode.generate(qr, { small: true });
      console.log("\n");
    }

    if (connection === "open") {
      logger.info("✅ WhatsApp connected successfully!");
      console.log("\n");
      console.log("═══════════════════════════════════════════════════");
      console.log("  ✅ WHATSAPP CONNECTED SUCCESSFULLY!");
      console.log("  Bot is now listening for messages...");
      console.log("═══════════════════════════════════════════════════");
      console.log("\n");
    }

    if (connection === "close") {
      const statusCode =
        lastDisconnect?.error?.output?.statusCode ||
        lastDisconnect?.error?.output?.payload?.statusCode;

      const shouldReconnect = statusCode !== DisconnectReason.loggedOut;

      logger.warn(
        { statusCode, shouldReconnect },
        "WhatsApp connection closed"
      );

      if (shouldReconnect) {
        logger.info("Reconnecting in 3 seconds...");
        setTimeout(startWhatsApp, 3000);
      } else {
        logger.error(
          "Logged out from WhatsApp. Delete the auth_info folder and restart to re-scan QR."
        );
        process.exit(1);
      }
    }
  });

  // Save auth credentials whenever they update
  sock.ev.on("creds.update", saveCreds);

  // ── Incoming messages ──────────────────────────────────────────────────

  sock.ev.on("messages.upsert", async ({ messages, type }) => {
    // Only process new messages (not history sync)
    if (type !== "notify") return;

    for (const msg of messages) {
      // Skip messages from self, status broadcasts, and non-text messages
      if (msg.key.fromMe) continue;
      if (msg.key.remoteJid === "status@broadcast") continue;

      // Extract text content
      const text =
        msg.message?.conversation ||
        msg.message?.extendedTextMessage?.text ||
        msg.message?.imageMessage?.caption ||
        msg.message?.videoMessage?.caption ||
        "";

      if (!text.trim()) {
        logger.debug({ msg: msg.key }, "Skipping non-text message");
        continue;
      }

      // Extract phone number from JID (e.g., 919999999999@s.whatsapp.net → +919999999999)
      const rawJid = msg.key.remoteJid || "";
      const phone = "+" + rawJid.replace("@s.whatsapp.net", "");
      const pushName = msg.pushName || "";

      logger.info(
        { phone, pushName, messagePreview: text.substring(0, 60) },
        "Incoming WhatsApp message"
      );

      // Forward to backend
      try {
        await forwardToBackend(phone, text, pushName);
      } catch (err) {
        logger.error({ err, phone }, "Failed to process message");

        // Send a fallback error message to the user
        try {
          const jid = rawJid;
          await sock.sendMessage(jid, {
            text:
              "I apologize, but I'm experiencing a temporary issue. " +
              "Please try again in a moment, or reach out to us at " +
              "support@pp5mediasolutions.com or WhatsApp +91 99593 94534.",
          });
        } catch (sendErr) {
          logger.error({ sendErr }, "Failed to send error reply");
        }
      }
    }
  });
}

// ─── Start everything ───────────────────────────────────────────────────────

async function main() {
  // Start Express server
  app.listen(BAILEYS_PORT, () => {
    logger.info(
      { port: BAILEYS_PORT },
      `Baileys HTTP server listening on port ${BAILEYS_PORT}`
    );
    console.log(`\n🚀 Baileys send endpoint ready at http://localhost:${BAILEYS_PORT}/send\n`);
  });

  // Start WhatsApp connection
  await startWhatsApp();
}

main().catch((err) => {
  logger.error({ err }, "Fatal error starting Baileys service");
  process.exit(1);
});
