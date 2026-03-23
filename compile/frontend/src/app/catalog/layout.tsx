import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Catalog",
  description:
    "Browse compiled behaviors and 50 functional modules of the Drosophila brain. Each behavior was compiled by directed evolution — new ones are added as they're discovered.",
  openGraph: {
    title: "Catalog | Compile",
    description:
      "Compiled behaviors and functional modules of the fly brain.",
  },
};

export default function CatalogLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
