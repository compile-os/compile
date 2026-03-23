import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Careers",
  description:
    "Join the team designing biological brains. Open roles in computational neuroscience and platform engineering.",
  openGraph: {
    title: "Careers | Compile",
    description:
      "Join us. We design biological brains.",
  },
};

export default function CareersLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
