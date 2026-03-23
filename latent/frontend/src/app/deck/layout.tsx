import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Deck",
  description:
    "We design biological brains. Synthetic neuroscience starts now.",
  robots: {
    index: false,
    follow: false,
  },
};

export default function DeckLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
