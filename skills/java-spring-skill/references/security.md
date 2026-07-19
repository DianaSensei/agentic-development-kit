# Spring Security 6 — JWT, Method Security, OAuth2

## Security Filter Chain

```java
@Configuration
@EnableWebSecurity
@EnableMethodSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
            .csrf(csrf -> csrf.ignoringRequestMatchers("/api/auth/**")) // stateless JWT APIs usually disable CSRF for auth endpoints; if there are other session-based endpoints, keep CSRF enabled for those
            .cors(cors -> cors.configurationSource(corsConfigurationSource()))
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/auth/**", "/actuator/health").permitAll()
                .requestMatchers("/api/admin/**").hasRole("ADMIN")
                .anyRequest().authenticated())
            .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .addFilterBefore(jwtAuthenticationFilter(), UsernamePasswordAuthenticationFilter.class);
        return http.build();
    }

    @Bean
    public CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration configuration = new CorsConfiguration();
        configuration.setAllowedOrigins(List.of("http://localhost:3000"));
        configuration.setAllowedMethods(List.of("GET", "POST", "PUT", "DELETE", "OPTIONS"));
        configuration.setAllowedHeaders(List.of("*"));
        configuration.setAllowCredentials(true);
        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", configuration);
        return source;
    }

    @Bean
    public AuthenticationManager authenticationManager(AuthenticationConfiguration config) throws Exception {
        return config.getAuthenticationManager();
    }

    @Bean
    public PasswordEncoder passwordEncoder() { return new BCryptPasswordEncoder(12); }
}
```

## JWT Filter + Service

```java
@Component
@RequiredArgsConstructor
public class JwtAuthenticationFilter extends OncePerRequestFilter {
    private final JwtService jwtService;
    private final UserDetailsService userDetailsService;

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        String authHeader = request.getHeader("Authorization");
        if (authHeader == null || !authHeader.startsWith("Bearer ")) {
            chain.doFilter(request, response);
            return;
        }
        String jwt = authHeader.substring(7);
        try {
            String username = jwtService.extractUsername(jwt);
            if (username != null && SecurityContextHolder.getContext().getAuthentication() == null) {
                UserDetails userDetails = userDetailsService.loadUserByUsername(username);
                if (jwtService.isTokenValid(jwt, userDetails)) {
                    var authToken = new UsernamePasswordAuthenticationToken(userDetails, null, userDetails.getAuthorities());
                    authToken.setDetails(new WebAuthenticationDetailsSource().buildDetails(request));
                    SecurityContextHolder.getContext().setAuthentication(authToken);
                }
            }
        } catch (JwtException e) {
            log.error("JWT validation failed", e);
        }
        chain.doFilter(request, response);
    }
}

@Service
public class JwtService {
    @Value("${jwt.secret}") private String secretKey;
    @Value("${jwt.expiration}") private long jwtExpiration;

    public String extractUsername(String token) { return extractClaim(token, Claims::getSubject); }

    public <T> T extractClaim(String token, Function<Claims, T> resolver) {
        return resolver.apply(extractAllClaims(token));
    }

    public String generateToken(UserDetails userDetails) {
        return Jwts.builder()
            .setSubject(userDetails.getUsername())
            .setIssuedAt(new Date())
            .setExpiration(new Date(System.currentTimeMillis() + jwtExpiration))
            .signWith(getSignInKey(), SignatureAlgorithm.HS256)
            .compact();
    }

    public boolean isTokenValid(String token, UserDetails userDetails) {
        return extractUsername(token).equals(userDetails.getUsername())
            && extractClaim(token, Claims::getExpiration).after(new Date());
    }

    private Claims extractAllClaims(String token) {
        return Jwts.parserBuilder().setSigningKey(getSignInKey()).build().parseClaimsJws(token).getBody();
    }

    private Key getSignInKey() { return Keys.hmacShaKeyFor(Decoders.BASE64.decode(secretKey)); }
}
```

`jwt.secret` MUST be read from an environment variable/secret manager (`${JWT_SECRET}`), not hardcoded in `application.yml` — a security risk if the config file is ever committed.

## UserDetailsService + Authentication Service

```java
@Service
@RequiredArgsConstructor
public class CustomUserDetailsService implements UserDetailsService {
    private final UserRepository userRepository;

    @Override
    public UserDetails loadUserByUsername(String email) {
        return userRepository.findByEmailWithRoles(email)
            .map(user -> org.springframework.security.core.userdetails.User.builder()
                .username(user.getEmail())
                .password(user.getPassword())
                .authorities(user.getRoles().stream().map(r -> new SimpleGrantedAuthority("ROLE_" + r.getName())).toList())
                .disabled(!user.getActive())
                .build())
            .orElseThrow(() -> new UsernameNotFoundException("User not found: " + email));
    }
}

@Service
@RequiredArgsConstructor
@Transactional
public class AuthenticationService {
    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtService jwtService;
    private final AuthenticationManager authenticationManager;

    public AuthenticationResponse register(RegisterRequest request) {
        if (userRepository.existsByEmail(request.email())) {
            throw new DuplicateResourceException("Email already registered");
        }
        User user = userRepository.save(User.builder()
            .email(request.email())
            .password(passwordEncoder.encode(request.password()))
            .roles(Set.of(Role.builder().name("USER").build()))
            .active(true)
            .build());
        return new AuthenticationResponse(jwtService.generateToken(toUserDetails(user)));
    }

    public AuthenticationResponse login(LoginRequest request) {
        authenticationManager.authenticate(new UsernamePasswordAuthenticationToken(request.email(), request.password()));
        User user = userRepository.findByEmail(request.email()).orElseThrow();
        return new AuthenticationResponse(jwtService.generateToken(toUserDetails(user)));
    }

    private UserDetails toUserDetails(User user) {
        return org.springframework.security.core.userdetails.User.builder()
            .username(user.getEmail()).password(user.getPassword())
            .authorities(user.getRoles().stream().map(r -> new SimpleGrantedAuthority("ROLE_" + r.getName())).toList())
            .build();
    }
}
```

## Method-Level Security

```java
@Service
@RequiredArgsConstructor
public class UserService {
    @PreAuthorize("hasRole('ADMIN')")
    public List<User> getAllUsers() { return userRepository.findAll(); }

    @PreAuthorize("hasRole('ADMIN') or #userId == authentication.principal.id")
    public User getUserById(Long userId) {
        return userRepository.findById(userId).orElseThrow(() -> new ResourceNotFoundException("User not found"));
    }

    @PostAuthorize("returnObject.email == authentication.principal.username or hasRole('ADMIN')")
    public User findUserByEmail(String email) {
        return userRepository.findByEmail(email).orElseThrow();
    }
}
```

`@PreAuthorize` checks BEFORE the method runs (use when the condition is known from the input parameters); `@PostAuthorize` checks AFTER a result is returned (use when the condition depends on the returned object itself, e.g. a user can only view their own record).

## OAuth2 Resource Server (JWT issued by an external IdP — e.g. Keycloak/Auth0/Cognito)

Use this when the project does NOT issue its own JWTs (unlike the JwtService above) but instead validates tokens issued by an external Identity Provider.

```java
@Configuration
@EnableWebSecurity
public class OAuth2ResourceServerConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http.authorizeHttpRequests(auth -> auth
                .requestMatchers("/public/**").permitAll()
                .anyRequest().authenticated())
            .oauth2ResourceServer(oauth2 -> oauth2.jwt(jwt -> jwt.jwtAuthenticationConverter(jwtAuthenticationConverter())));
        return http.build();
    }

    @Bean
    public JwtDecoder jwtDecoder() { return JwtDecoders.fromIssuerLocation("https://auth.example.com"); }

    @Bean
    public JwtAuthenticationConverter jwtAuthenticationConverter() {
        var grantedAuthoritiesConverter = new JwtGrantedAuthoritiesConverter();
        grantedAuthoritiesConverter.setAuthoritiesClaimName("roles");
        grantedAuthoritiesConverter.setAuthorityPrefix("ROLE_");
        var converter = new JwtAuthenticationConverter();
        converter.setJwtGrantedAuthoritiesConverter(grantedAuthoritiesConverter);
        return converter;
    }
}
```

## Security Utility (read the current user outside of `@AuthenticationPrincipal`)

```java
@Component("userSecurityService")
public class UserSecurityService {
    public String getCurrentUsername() {
        var auth = SecurityContextHolder.getContext().getAuthentication();
        return (auth != null && auth.getPrincipal() instanceof UserDetails ud) ? ud.getUsername() : null;
    }
}
```

## Quick Reference

| Annotation | Purpose |
|-----------|---------|
| `@EnableWebSecurity` / `@EnableMethodSecurity` | Enable HTTP-level / method-level security |
| `@PreAuthorize` / `@PostAuthorize` | Check permissions before/after a method runs |
| `@Secured` / `@RolesAllowed` | Role-based (older style than `@PreAuthorize`) |
| `SecurityContextHolder` | Access the current security context |
| `@AuthenticationPrincipal` | Inject the current user into a controller method |

## Security Best Practices

- HTTPS is mandatory in production, not just locally.
- Secrets (JWT signing key, DB password) must ALWAYS come from environment variables/secret managers, never hardcoded.
- `BCryptPasswordEncoder` strength should be at least 12.
- Have a refresh token mechanism instead of a long-lived access token.
- Rate-limit auth endpoints (login/register) specifically — a common brute-force target.
- Never log raw JWT/password values to standard logs.
