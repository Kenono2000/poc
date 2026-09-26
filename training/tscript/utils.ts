export type User = { id: string; name: string; email: string; age: number };
export function formatUser(u: User): string {
  return `${u.name} <${u.email}>`;
}