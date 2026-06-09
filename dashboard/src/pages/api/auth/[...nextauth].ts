import NextAuth from 'next-auth'; 
import DiscordProvider from 'next-auth/providers/discord'; 
 
const clientId = '1220462982384058370'; 
const clientSecret = '1HLuRei4-sSicHbn6vCLxuYgNJLQUmzc'; 
const nextAuthSecret = '9c5d92cc96942c13ea6eba37829e435569599dfdcc6e0cd186d9f9c63fcf195a'; 
 
const handler = NextAuth({ 
  providers: [ 
    DiscordProvider({ 
      clientId, 
      clientSecret, 
      authorization: { params: { scope: 'identify email guilds' } } 
    }) 
  ], 
  secret: nextAuthSecret, 
  callbacks: { 
    async jwt({ token, account }) { 
      if (account) token.accessToken = account.access_token; 
      return token; 
    }, 
    async session({ session, token }) { 
      session.accessToken = token.accessToken; 
      return session; 
    } 
  } 
}); 
 
export { handler as GET, handler as POST } 
