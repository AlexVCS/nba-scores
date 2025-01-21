import type {Metadata} from "next";
import {Inter} from "next/font/google";
import "./globals.css";
import {Providers} from "@/app/components/Providers";
import {ThemeProvider} from "next-themes";
import {TRPCProvider} from "@/app/api/trpc/client";

const inter = Inter({subsets: ["latin"]});

export const metadata: Metadata = {
  title: "NBA Scores",
  description: "Find out the scores around the NBA!",
};

export default function RootLayout({children}: {children: React.ReactNode}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <TRPCProvider>
          <Providers
            attribute="class"
            defaultTheme="system"
            enableSystem
            disableTransitionOnChange
          >
            {children}
          </Providers>
        </TRPCProvider>
      </body>
    </html>
  );
}
