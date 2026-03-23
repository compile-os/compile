import { Metadata } from "next";

export const metadata: Metadata = {
  title: "About",
  description:
    "We design biological brains. Compile is synthetic neuroscience.",
  openGraph: {
    title: "About | Compile",
    description:
      "We design biological brains. Compile is synthetic neuroscience.",
  },
};

export default function AboutLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
