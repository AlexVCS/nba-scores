import { z } from 'zod';
import { TRPCRouter } from '../init';
import { publicProcedure } from '@/app/api/trpc/init';
export const appRouter = TRPCRouter({
  hello: publicProcedure
    .input(
      z.object({
        text: z.string(),
      }),
    )
    .query((opts) => {
      return {
        greeting: `hello ${opts.input.text}`,
      };
    }),
});
// export type definition of API
export type AppRouter = typeof appRouter;