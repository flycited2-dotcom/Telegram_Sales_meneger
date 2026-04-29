import { syncItpImages } from "@/lib/itp/images";

syncItpImages()
  .then((result) => {
    console.log("images sync complete", result);
  })
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
