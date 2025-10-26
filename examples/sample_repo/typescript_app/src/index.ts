export const sum = (a: number, b: number): number => a + b;

if (require.main === module) {
  // eslint-disable-next-line no-console
  console.log(sum(2, 3));
}

