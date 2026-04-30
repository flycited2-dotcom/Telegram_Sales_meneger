import type { Metadata } from "next";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://climat-simf.ru"),
  title: {
    default: "БытТехОпт - техника, электроника и товары для дома под заказ",
    template: "%s | БытТехОпт",
  },
  description:
    "Интернет-магазин бытовой техники, электроники, климатического оборудования и товаров для дома с доставкой по Крыму, Херсонской и Запорожской областям.",
  keywords: [
    "БытТехОпт",
    "бытовая техника Симферополь",
    "электроника Крым",
    "климатическая техника",
    "доставка техники Херсонская область",
    "доставка техники Запорожская область",
  ],
  alternates: {
    canonical: "/",
  },
  openGraph: {
    title: "БытТехОпт - техника и электроника под заказ",
    description:
      "Большой каталог бытовой техники, электроники и товаров для дома. Доставка по Крыму, Херсонской и Запорожской областям, оплата при получении.",
    url: "/",
    siteName: "БытТехОпт",
    locale: "ru_RU",
    type: "website",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ru" className="h-full antialiased">
      <body className="flex min-h-full flex-col bg-stone-50 text-zinc-950">
        <SiteHeader />
        <main className="flex-1">{children}</main>
        <SiteFooter />
      </body>
    </html>
  );
}
