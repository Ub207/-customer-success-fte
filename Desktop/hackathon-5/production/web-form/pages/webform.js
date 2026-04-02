import Head from 'next/head';
import WebFormDashboard from '../components/WebFormDashboard';

export default function WebFormPage() {
  return (
    <>
      <Head>
        <title>Web Form Channel — TechCorp AI Support</title>
        <meta name="description" content="Web Form ticket dashboard — AI Customer Success FTE" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>
      <WebFormDashboard />
    </>
  );
}
