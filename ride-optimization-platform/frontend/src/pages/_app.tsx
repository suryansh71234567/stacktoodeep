import '../styles/globals.css'; // <--- CHANGED THIS LINE
import type { AppProps } from 'next/app';
import Head from 'next/head';

export default function App({ Component, pageProps }: AppProps) {
  return (
    <>
      <Head>
        <title>Nexus Agent | Ride Optimization</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>
      <Component {...pageProps} />
    </>
  );
}