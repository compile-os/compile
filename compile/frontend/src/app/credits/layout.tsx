import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Credits",
  description:
    "Acknowledgments for the data, tools, and research that made Compile possible. FlyWire, Eon Systems, Virtual Fly Brain, and the open neuroscience community.",
  openGraph: {
    title: "Credits | Compile",
    description: "Acknowledgments for the data and tools behind Compile.",
  },
};

export default function CreditsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
