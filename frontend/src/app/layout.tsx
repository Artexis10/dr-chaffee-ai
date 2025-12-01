import '../styles/globals.css'

export const metadata = {
  title: 'Ask Dr Chaffee',
  description: 'Interactive Knowledge Base',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="bg-slate-900 text-white">{children}</body>
    </html>
  )
}
