import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Playground",
  description:
    "Design neural circuits interactively. Select a behavior, see the exact wiring changes, and watch the fly execute it in 3D.",
  openGraph: {
    title: "Playground | Compile",
    description:
      "Interactive circuit design. Select a behavior, see the wiring changes and 3D behavior.",
  },
};

export default function PlaygroundLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
