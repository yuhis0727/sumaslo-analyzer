"use client";
export default function Head() {
    return (
      <>
        <title>fast-fullstack-template</title>
        <meta content="width=device-width, initial-scale=1" name="viewport" />
        <meta name="description" content="samples ..." />
        <link rel="icon" href={process.env.NEXT_PUBLIC_FAVICON_PATH} />
        <meta httpEquiv="Content-Security-Policy" content="upgrade-insecure-requests" />
      </>
    );
}
