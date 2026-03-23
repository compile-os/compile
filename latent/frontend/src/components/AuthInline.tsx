"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Key, Loader2 } from "lucide-react";
import { startRegistration, startAuthentication } from "@simplewebauthn/browser";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

interface AuthInlineProps {
  isDark?: boolean;
  compact?: boolean;
  onSuccess?: (user: any, token: string) => void;
}

export function AuthInline({ isDark = true, compact = false, onSuccess }: AuthInlineProps) {
  const [expanded, setExpanded] = useState(false);
  const [username, setUsername] = useState("");
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<"idle" | "new" | "existing">("idle");

  const textMuted = isDark ? "text-gray-400" : "text-gray-600";

  const handleSubmit = async () => {
    if (!username.trim() || username.length < 3) return;

    setLoading(true);
    try {
      // Check if user exists
      const checkRes = await fetch(`${API_URL}/api/v1/auth/passkey/check?username=${encodeURIComponent(username)}`);
      const { exists } = await checkRes.json();

      if (exists) {
        // Login flow
        const beginRes = await fetch(`${API_URL}/api/v1/auth/passkey/login/begin`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username }),
        });
        const { options, user_id, session_id } = await beginRes.json();
        const assertion = await startAuthentication(options.publicKey);

        const finishRes = await fetch(`${API_URL}/api/v1/auth/passkey/login/finish`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id, user_id, ...assertion }),
        });
        const result = await finishRes.json();
        onSuccess?.(result.user, result.token);
      } else {
        // Register flow
        const beginRes = await fetch(`${API_URL}/api/v1/auth/passkey/register/begin`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, display_name: username }),
        });
        const { options, user_id, session_id } = await beginRes.json();
        const credential = await startRegistration(options.publicKey);

        const finishRes = await fetch(`${API_URL}/api/v1/auth/passkey/register/finish`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id,
            user_id,
            credential_name: `${navigator.platform}`,
            ...credential,
          }),
        });
        const result = await finishRes.json();
        onSuccess?.(result.user, result.token);
      }
      setExpanded(false);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (!expanded) {
    return (
      <button
        onClick={() => setExpanded(true)}
        className={compact
          ? "text-[10px] bg-purple-600 hover:bg-purple-500 text-white px-2.5 py-1 rounded-md transition"
          : "text-sm bg-purple-600 hover:bg-purple-500 text-white px-4 py-2 rounded-lg transition"
        }
      >
        {compact ? "Sign in" : "Get Access"}
      </button>
    );
  }

  return (
    <motion.div
      initial={{ width: 100, opacity: 0 }}
      animate={{ width: 220, opacity: 1 }}
      className="flex items-center gap-2"
    >
      <input
        type="text"
        value={username}
        onChange={(e) => setUsername(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ""))}
        onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
        placeholder="username"
        autoFocus
        className={`w-32 px-3 py-2 text-sm rounded-lg ${
          isDark ? "bg-white/10 text-white placeholder:text-gray-500" : "bg-gray-100 text-gray-900 placeholder:text-gray-400"
        } border-none outline-none`}
      />
      <button
        onClick={handleSubmit}
        disabled={loading || username.length < 3}
        className="p-2 bg-purple-600 hover:bg-purple-500 disabled:bg-purple-600/50 text-white rounded-lg transition"
      >
        {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Key className="w-4 h-4" />}
      </button>
      <button
        onClick={() => setExpanded(false)}
        className={`text-xs ${textMuted} hover:text-white`}
      >
        cancel
      </button>
    </motion.div>
  );
}

export default AuthInline;
