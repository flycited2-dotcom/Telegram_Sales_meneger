import { prisma } from "@/lib/db";
import { isAllowedSupplierImageUrl } from "@/lib/product-images";

export const dynamic = "force-dynamic";

type RouteContext = {
  params: Promise<{ id: string }>;
};

function placeholderImageResponse(): Response {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="800" height="800" viewBox="0 0 800 800">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#f4f4f5"/>
      <stop offset="52%" stop-color="#e7f5f1"/>
      <stop offset="100%" stop-color="#fff7ed"/>
    </linearGradient>
  </defs>
  <rect width="800" height="800" rx="32" fill="url(#bg)"/>
  <text x="400" y="372" text-anchor="middle" font-family="Arial, sans-serif" font-size="96" font-weight="800" fill="#d4d4d8">БТО</text>
  <text x="400" y="440" text-anchor="middle" font-family="Arial, sans-serif" font-size="28" font-weight="600" fill="#71717a">Фото скоро появится</text>
</svg>`;

  return new Response(svg, {
    status: 200,
    headers: {
      "Cache-Control": "public, max-age=3600",
      "Content-Type": "image/svg+xml; charset=utf-8",
    },
  });
}

export async function GET(request: Request, { params }: RouteContext) {
  const { id } = await params;
  const image = await prisma.productImage.findFirst({
    where: {
      id,
      deleted: false,
    },
    select: {
      localImageUrl: true,
      supplierImageUrl: true,
    },
  });

  if (!image) {
    return new Response("Not found", { status: 404 });
  }

  if (image.localImageUrl?.startsWith("/")) {
    return Response.redirect(new URL(image.localImageUrl, request.url));
  }

  const sourceUrl = image.localImageUrl ?? image.supplierImageUrl;
  if (!isAllowedSupplierImageUrl(sourceUrl)) {
    return placeholderImageResponse();
  }

  const upstream = await fetch(sourceUrl, {
    cache: "force-cache",
    next: {
      revalidate: 86400,
    },
  }).catch(() => null);

  if (!upstream?.ok || !upstream.body) {
    return placeholderImageResponse();
  }

  const headers = new Headers();
  headers.set("Cache-Control", "public, max-age=86400, stale-while-revalidate=604800");
  headers.set("Content-Type", upstream.headers.get("Content-Type") ?? "image/jpeg");

  return new Response(upstream.body, {
    status: 200,
    headers,
  });
}
