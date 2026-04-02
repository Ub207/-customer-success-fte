import Head from 'next/head';
import WhatsAppDashboard from '../components/WhatsAppDashboard';

export default function WhatsAppPage() {
  return (
    <>
      <Head>
        <title>WhatsApp Channel — TechCorp AI Support</title>
        <meta name="description" content="WhatsApp channel dashboard — AI Customer Success FTE" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>
      <WhatsAppDashboard />
    </>
  );
}
