import { syncItpImages } from "@/lib/itp/images";

const limit = Number(process.env.ITP_IMAGE_SYNC_LIMIT ?? process.argv[2] ?? 1000);

syncItpImages(Number.isFinite(limit) ? limit : 1000)
  .then((result) => {
    console.log("images sync complete", result);
  })
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
