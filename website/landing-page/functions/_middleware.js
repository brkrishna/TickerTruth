const CANONICAL_HOST = "tickertruth.com";

export async function onRequest(context) {
  const url = new URL(context.request.url);

  if (url.hostname !== CANONICAL_HOST && url.hostname.endsWith(".pages.dev")) {
    url.hostname = CANONICAL_HOST;
    url.protocol = "https:";
    return Response.redirect(url.toString(), 301);
  }

  return context.next();
}
