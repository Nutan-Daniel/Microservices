export default function NotFound() {
  return (
    <div className="max-w-md mx-auto p-8 text-center">
      <h1 className="text-2xl font-bold">404 - Not Found</h1>
      <p className="text-slate-600">The page you are looking for does not exist.</p>
      <a href="/" className="mt-4 inline-block text-blue-600 hover:underline">Go home</a>
    </div>
  )
}