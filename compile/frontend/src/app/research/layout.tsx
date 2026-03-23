import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Research",
  description:
    "Can we design biological neural circuits to specification? Directed evolution on the FlyWire connectome reveals a behavior-dependent modifiability landscape and the evolvable surface of complete brains.",
  openGraph: {
    title: "Research | Compile",
    description:
      "Behavior-dependent modifiability across complete connectomes. Validated against experimental neuroscience -- DNa02, LPLC2, visual sensory modules recovered with zero labels.",
  },
};

export default function ResearchLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
