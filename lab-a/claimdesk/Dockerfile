FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /src
COPY pom.xml .
RUN mvn -q -B dependency:go-offline
COPY src src
RUN mvn -q -B package -DskipTests

# JDK (not JRE): the ops team uses jcmd/jstack in the container.
FROM eclipse-temurin:17-jdk
WORKDIR /app
COPY --from=build /src/target/claimdesk.jar /app/claimdesk.jar
COPY documents /app/documents
ENV CLAIMDESK_SMTP_PASSWORD=Hb-smtp-2024!relay
EXPOSE 8085
CMD ["java", "-jar", "/app/claimdesk.jar"]
