/** @type {import('next').NextConfig} */
module.exports = {
  env: {
    TZ: "America/New_York",
  },
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "upload.wikimedia.org",
        port: "",
      },
    ],
  },
};
