import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Documentation",
  description:
    "Compile API documentation. Load connectomes, run evolution, map the modifiability landscape.",
  openGraph: {
    title: "Documentation | Compile",
    description:
      "API documentation for Compile. Load connectomes, define behaviors, run evolution, extract wiring changes.",
  },
};

export default function DocsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
