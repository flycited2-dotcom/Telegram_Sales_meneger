import type { Prisma } from "@prisma/client";

export const degradedRetailNameTerms = [
  "поврежденная упаковка",
  "повреждённая упаковка",
  "уценка",
  "витринный образец",
  "б/у",
  "некондиция",
];

export function isDegradedRetailName(name: string | null | undefined): boolean {
  const normalized = (name ?? "").toLocaleLowerCase("ru-RU");
  return degradedRetailNameTerms.some((term) => normalized.includes(term));
}

export function normalRetailNameWhere(): Prisma.ProductWhereInput {
  return {
    NOT: degradedRetailNameTerms.map((term) => ({
      OR: [
        { name: { contains: term, mode: "insensitive" } },
        { supplierName: { contains: term, mode: "insensitive" } },
      ],
    })),
  };
}
