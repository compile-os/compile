import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  metadataBase: new URL("https://compile.now"),
  title: {
    default: "Compile - We Design Biological Brains",
    template: "%s | Compile",
  },
  description: "Compile is synthetic neuroscience. Specify a cognitive capability, compile it to a circuit, grow it from a developmental program. Validated on fly and mouse connectomes. Open source.",
  keywords: [
    "BCI",
    "brain-computer interface",
    "synthetic neuroscience",
    "connectome evolution",
    "connectome",
    "FlyWire",
    "biological brain design",
    "modifiability landscape",
    "evolvable surface",
    "neural circuit design",
    "connectome design",
    "directed evolution",
    "neural architecture",
    "computational neuroscience",
    "neurotechnology",
    "brain simulation",
    "neurotech",
    "compositional neural architecture",
  ],
  authors: [{ name: "Compile" }],
  creator: "Compile",
  publisher: "Compile",
  formatDetection: {
    email: false,
    address: false,
    telephone: false,
  },
  openGraph: {
    type: "website",
    locale: "en_US",
    url: "https://compile.now",
    siteName: "Compile",
    title: "Compile - We Design Biological Brains",
    description: "Compile is synthetic neuroscience. Specify a cognitive capability, compile it to a circuit, grow it from a developmental program. Validated on fly and mouse connectomes. Open source.",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "Compile - We Design Biological Brains",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Compile - We Design Biological Brains",
    description: "Compile is synthetic neuroscience. Specify a cognitive capability, compile it to a circuit, grow it from a developmental program. Validated on fly and mouse connectomes. Open source.",
    images: ["/og-image.png"],
    creator: "@compilenow",
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
  alternates: {
    canonical: "https://compile.now",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="icon" href="/favicon.ico" sizes="any" />
        <link rel="icon" href="/icon.svg" type="image/svg+xml" />
        <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
        <link rel="manifest" href="/manifest.json" />
        <meta name="theme-color" content="#000000" />
      </head>
      <body className={inter.className}>{children}</body>
    </html>
  );
}
