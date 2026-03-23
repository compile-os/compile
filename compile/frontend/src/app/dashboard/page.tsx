"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Key,
  Activity,
  Code,
  Copy,
  Check,
  Plus,
  Trash2,
  BarChart3,
  Settings,
  LogOut,
  Fingerprint,
} from "lucide-react";

interface User {
  id: string;
  username: string;
  display_name?: string;
  email?: string;
  plan: string;
}

interface APIKey {
  id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  created_at: string;
  last_used?: string;
}

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [apiKeys, setApiKeys] = useState<APIKey[]>([]);
  const [newKeyName, setNewKeyName] = useState("");
  const [showNewKeyModal, setShowNewKeyModal] = useState(false);
  const [newKeyValue, setNewKeyValue] = useState<string | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "keys" | "usage" | "settings">(
    "overview"
  );

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

  useEffect(() => {
    const token = localStorage.getItem("token");
    const userData = localStorage.getItem("user");

    if (!token) {
      router.push("/login");
      return;
    }

    if (userData) {
      setUser(JSON.parse(userData));
    }

    // Fetch API keys
    fetchAPIKeys(token);
  }, [router]);

  const fetchAPIKeys = async (token: string) => {
    try {
      const response = await fetch(`${API_URL}/api/v1/api-keys`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setApiKeys(data.api_keys || []);
      }
    } catch (error) {
      console.error("Failed to fetch API keys:", error);
    }
  };

  const createAPIKey = async () => {
    const token = localStorage.getItem("token");
    if (!token || !newKeyName) return;

    try {
      const response = await fetch(`${API_URL}/api/v1/api-keys`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ name: newKeyName }),
      });

      if (response.ok) {
        const data = await response.json();
        setNewKeyValue(data.key);
        fetchAPIKeys(token);
        setNewKeyName("");
      }
    } catch (error) {
      console.error("Failed to create API key:", error);
    }
  };

  const deleteAPIKey = async (keyId: string) => {
    const token = localStorage.getItem("token");
    if (!token) return;

    try {
      await fetch(`${API_URL}/api/v1/api-keys/${keyId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      fetchAPIKeys(token);
    } catch (error) {
      console.error("Failed to delete API key:", error);
    }
  };

  const copyToClipboard = (text: string, keyId: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(keyId);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const logout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    router.push("/");
  };

  if (!user) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-purple-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Sidebar */}
      <aside className="fixed left-0 top-0 bottom-0 w-64 bg-gray-950 border-r border-white/10 flex flex-col">
        <div className="p-6 border-b border-white/10">
          <Link href="/" className="flex items-center gap-2">
            <svg width="32" height="32" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="50" cy="50" r="45" stroke="#a855f7" strokeWidth="2" opacity="0.5" />
              <circle cx="50" cy="50" r="35" stroke="#c084fc" strokeWidth="2" opacity="0.7" />
              <circle cx="50" cy="50" r="25" fill="#a855f7" opacity="0.3" />
              <text x="50" y="60" textAnchor="middle" fill="white" fontSize="30" fontFamily="monospace" fontWeight="bold">{"</>"}</text>
            </svg>
            <span className="font-bold text-xl">Run</span>
          </Link>
        </div>

        <nav className="flex-1 p-4">
          <ul className="space-y-1">
            {[
              { id: "overview", icon: BarChart3, label: "Overview" },
              { id: "keys", icon: Key, label: "API Keys" },
              { id: "usage", icon: Activity, label: "Usage" },
              { id: "settings", icon: Settings, label: "Settings" },
            ].map((item) => (
              <li key={item.id}>
                <button
                  onClick={() => setActiveTab(item.id as typeof activeTab)}
                  className={`w-full flex items-center gap-3 px-4 py-2 rounded-lg transition ${
                    activeTab === item.id
                      ? "bg-purple-500/20 text-purple-400"
                      : "text-gray-400 hover:bg-white/5"
                  }`}
                >
                  <item.icon className="w-5 h-5" />
                  {item.label}
                </button>
              </li>
            ))}
          </ul>
        </nav>

        <div className="p-4 border-t border-white/10">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-full bg-purple-500/20 flex items-center justify-center">
              <span className="text-purple-400 font-medium">
                {user.username[0]?.toUpperCase()}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-medium truncate">{user.display_name || user.username}</p>
              <p className="text-sm text-gray-400 truncate">@{user.username}</p>
            </div>
          </div>
          <button
            onClick={logout}
            className="w-full flex items-center gap-2 px-4 py-2 rounded-lg text-gray-400 hover:bg-white/5 transition"
          >
            <LogOut className="w-5 h-5" />
            Sign out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="ml-64 min-h-screen p-8">
        {activeTab === "overview" && (
          <div>
            <h1 className="text-3xl font-bold mb-8">Dashboard</h1>

            <div className="grid md:grid-cols-3 gap-6 mb-8">
              {[
                { label: "API Calls Today", value: "1,234", change: "+12%" },
                { label: "Active Models", value: "2", change: "" },
                { label: "Channel Hours", value: "23.5", change: "+8%" },
              ].map((stat) => (
                <div
                  key={stat.label}
                  className="p-6 rounded-xl bg-white/5 border border-white/10"
                >
                  <p className="text-sm text-gray-400 mb-1">{stat.label}</p>
                  <div className="flex items-baseline gap-2">
                    <span className="text-3xl font-bold">{stat.value}</span>
                    {stat.change && (
                      <span className="text-sm text-green-400">{stat.change}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Quick Start */}
            <div className="p-6 rounded-xl bg-gradient-to-r from-purple-500/10 to-pink-500/10 border border-purple-500/20 mb-8">
              <h2 className="text-xl font-semibold mb-4">Quick Start</h2>
              <div className="bg-black/50 rounded-lg p-4 mb-4">
                <pre className="text-sm text-gray-300 overflow-x-auto">
{`pip install run-sdk

import run
client = run.Client(api_key="your-api-key")

embedding = client.embed(
    signals,
    device_type="eeg",
    sample_rate=256
)`}
                </pre>
              </div>
              <Link
                href="/docs"
                className="inline-flex items-center gap-2 text-purple-400 hover:text-purple-300"
              >
                <Code className="w-4 h-4" />
                View full documentation
              </Link>
            </div>
          </div>
        )}

        {activeTab === "keys" && (
          <div>
            <div className="flex items-center justify-between mb-8">
              <h1 className="text-3xl font-bold">API Keys</h1>
              <button
                onClick={() => setShowNewKeyModal(true)}
                className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg transition"
              >
                <Plus className="w-5 h-5" />
                Create Key
              </button>
            </div>

            {newKeyValue && (
              <div className="mb-6 p-4 rounded-lg bg-green-500/10 border border-green-500/20">
                <p className="text-sm text-green-400 mb-2">
                  Your new API key has been created. Copy it now — you won&apos;t
                  see it again!
                </p>
                <div className="flex items-center gap-2">
                  <code className="flex-1 px-3 py-2 bg-black/50 rounded font-mono text-sm">
                    {newKeyValue}
                  </code>
                  <button
                    onClick={() => {
                      copyToClipboard(newKeyValue, "new");
                      setNewKeyValue(null);
                    }}
                    className="p-2 bg-white/10 rounded hover:bg-white/20 transition"
                  >
                    {copiedKey === "new" ? (
                      <Check className="w-5 h-5 text-green-400" />
                    ) : (
                      <Copy className="w-5 h-5" />
                    )}
                  </button>
                </div>
              </div>
            )}

            <div className="space-y-4">
              {apiKeys.map((key) => (
                <div
                  key={key.id}
                  className="p-4 rounded-xl bg-white/5 border border-white/10 flex items-center justify-between"
                >
                  <div>
                    <p className="font-medium">{key.name}</p>
                    <div className="flex items-center gap-4 text-sm text-gray-400 mt-1">
                      <code>{key.key_prefix}...</code>
                      <span>Created {new Date(key.created_at).toLocaleDateString()}</span>
                      {key.last_used && (
                        <span>
                          Last used {new Date(key.last_used).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => deleteAPIKey(key.id)}
                    className="p-2 text-red-400 hover:bg-red-500/10 rounded transition"
                  >
                    <Trash2 className="w-5 h-5" />
                  </button>
                </div>
              ))}

              {apiKeys.length === 0 && (
                <div className="text-center py-12 text-gray-400">
                  <Key className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>No API keys yet. Create one to get started.</p>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === "usage" && (
          <div>
            <h1 className="text-3xl font-bold mb-8">Usage</h1>

            <div className="grid md:grid-cols-2 gap-6 mb-8">
              <div className="p-6 rounded-xl bg-white/5 border border-white/10">
                <h3 className="font-semibold mb-4">Current Period</h3>
                <div className="space-y-4">
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-400">Inference Units</span>
                      <span>145,230 / 1,000,000</span>
                    </div>
                    <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-purple-500 rounded-full"
                        style={{ width: "14.5%" }}
                      />
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-400">Channel Hours</span>
                      <span>23.5 / 100</span>
                    </div>
                    <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-purple-500 rounded-full"
                        style={{ width: "23.5%" }}
                      />
                    </div>
                  </div>
                </div>
              </div>

              <div className="p-6 rounded-xl bg-white/5 border border-white/10">
                <h3 className="font-semibold mb-4">Estimated Cost</h3>
                <div className="text-4xl font-bold mb-2">$45.50</div>
                <p className="text-sm text-gray-400">This billing period</p>
              </div>
            </div>
          </div>
        )}

        {activeTab === "settings" && (
          <div>
            <h1 className="text-3xl font-bold mb-8">Settings</h1>

            <div className="max-w-2xl space-y-6">
              <div className="p-6 rounded-xl bg-white/5 border border-white/10">
                <h3 className="font-semibold mb-4">Profile</h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">
                      Username
                    </label>
                    <p className="font-medium">@{user.username}</p>
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">
                      Display Name
                    </label>
                    <p className="font-medium">{user.display_name || "Not set"}</p>
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Email</label>
                    <p className="font-medium">{user.email || "Not set"}</p>
                  </div>
                </div>
              </div>

              <div className="p-6 rounded-xl bg-white/5 border border-white/10">
                <h3 className="font-semibold mb-4 flex items-center gap-2">
                  <Fingerprint className="w-5 h-5 text-purple-400" />
                  Passkeys
                </h3>
                <p className="text-sm text-gray-400 mb-4">
                  Manage your passkeys for secure authentication.
                </p>
                <button className="flex items-center gap-2 px-4 py-2 border border-white/10 rounded-lg hover:bg-white/5 transition">
                  <Plus className="w-5 h-5" />
                  Add Another Passkey
                </button>
              </div>

              <div className="p-6 rounded-xl bg-white/5 border border-white/10">
                <h3 className="font-semibold mb-4">Plan</h3>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium capitalize">{user.plan} Plan</p>
                    <p className="text-sm text-gray-400">
                      {user.plan === "free"
                        ? "Limited API access"
                        : "Full API access"}
                    </p>
                  </div>
                  <Link
                    href="/pricing"
                    className="px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg transition"
                  >
                    Upgrade
                  </Link>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* New Key Modal */}
      {showNewKeyModal && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
          <div className="bg-gray-900 rounded-xl p-6 w-full max-w-md border border-white/10">
            <h2 className="text-xl font-semibold mb-4">Create API Key</h2>
            <input
              type="text"
              value={newKeyName}
              onChange={(e) => setNewKeyName(e.target.value)}
              placeholder="Key name (e.g., Production, Development)"
              className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none mb-4"
            />
            <div className="flex gap-3">
              <button
                onClick={() => setShowNewKeyModal(false)}
                className="flex-1 px-4 py-2 border border-white/10 rounded-lg hover:bg-white/5 transition"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  createAPIKey();
                  setShowNewKeyModal(false);
                }}
                disabled={!newKeyName}
                className="flex-1 px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg transition disabled:opacity-50"
              >
                Create
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
