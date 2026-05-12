import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Cluedo Solver",
  description: "Cluedo Solver takes the guesswork (and fun) out of Cluedo",
};

export default function RootLayout(
  props: Readonly<{
    children: React.ReactNode;
  }>,
) {
  return (
    <html lang="en">
      <body>{props.children}</body>
    </html>
  );
}
