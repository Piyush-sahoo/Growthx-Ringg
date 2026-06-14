import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "GrowthX × Ringg AI — Voice Agent Console",
  description: "Trigger Ringg AI outbound calls and review call outcomes.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
