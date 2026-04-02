import Head from 'next/head';
import GmailDashboard from '../components/GmailDashboard';

export default function GmailPage() {
  return (
    <>
      <Head>
        <title>Gmail Channel — TechCorp AI Support</title>
        <meta name="description" content="Gmail email channel dashboard — AI Customer Success FTE" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>
      <GmailDashboard />
    </>
  );
}
